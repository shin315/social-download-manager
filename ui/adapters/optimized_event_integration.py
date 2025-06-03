"""
Optimized Event System Integration for Adapter Framework

This module provides seamless integration between the high-performance event system
optimizer and the existing adapter framework, ensuring backward compatibility while
delivering significant performance improvements.

Key Features:
- Drop-in replacement for existing event coordination
- Backward compatibility with current adapter APIs
- Performance monitoring and metrics collection
- Graceful fallback to legacy system if needed
- Configuration-based optimization levels
"""

import sys
import logging
from typing import Dict, Any, Optional, Callable, List, Union
from pathlib import Path
from dataclasses import asdict
from threading import Lock
import json
import time

# Add performance module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts_dev" / "performance"))

try:
    from event_system_optimizer import (
        HighPerformanceEventBridge,
        EventPriority,
        EventMetrics,
        create_optimized_event_system
    )
    OPTIMIZER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Event system optimizer not available: {e}")
    OPTIMIZER_AVAILABLE = False

try:
    from .event_proxy import EventBridgeCoordinator
    from .interfaces import AdapterState
    from core.event_system import EventType, Event
except ImportError as e:
    print(f"Warning: Could not import adapter components: {e}")


class OptimizationLevel:
    """Performance optimization levels"""
    DISABLED = "disabled"
    BASIC = "basic"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


class OptimizedEventCoordinator:
    """
    Enhanced event coordinator with high-performance optimizations
    
    This class acts as a drop-in replacement for the existing EventBridgeCoordinator
    while providing significant performance improvements through:
    - Event batching and async processing
    - Object pooling and caching
    - Smart throttling and backpressure management
    - Comprehensive performance monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.optimization_level = self.config.get("optimization_level", OptimizationLevel.STANDARD)
        self.fallback_enabled = self.config.get("enable_fallback", True)
        self.metrics_enabled = self.config.get("enable_metrics", True)
        
        # Performance configuration based on optimization level
        self._performance_configs = {
            OptimizationLevel.DISABLED: {
                "max_workers": 1,
                "batch_size": 1,
                "max_cache_size": 0,
                "pool_size": 0
            },
            OptimizationLevel.BASIC: {
                "max_workers": 2,
                "batch_size": 10,
                "max_cache_size": 1000,
                "pool_size": 100
            },
            OptimizationLevel.STANDARD: {
                "max_workers": 4,
                "batch_size": 50,
                "max_cache_size": 5000,
                "pool_size": 1000
            },
            OptimizationLevel.AGGRESSIVE: {
                "max_workers": 6,
                "batch_size": 100,
                "max_cache_size": 10000,
                "pool_size": 2000
            },
            OptimizationLevel.MAXIMUM: {
                "max_workers": 8,
                "batch_size": 200,
                "max_cache_size": 20000,
                "pool_size": 5000
            }
        }
        
        # Initialize components
        self._optimized_bridge: Optional[HighPerformanceEventBridge] = None
        self._fallback_coordinator: Optional[EventBridgeCoordinator] = None
        self._metrics_history: List[Dict[str, Any]] = []
        self._metrics_lock = Lock()
        self._is_active = False
        self._use_optimized = False
        
        self.logger = logging.getLogger(__name__)
        
        # Try to initialize optimized system
        self._initialize_systems()
    
    def _initialize_systems(self) -> None:
        """Initialize optimized and fallback event systems"""
        
        # Initialize optimized system if available and not disabled
        if OPTIMIZER_AVAILABLE and self.optimization_level != OptimizationLevel.DISABLED:
            try:
                perf_config = self._performance_configs[self.optimization_level]
                self._optimized_bridge = create_optimized_event_system(perf_config)
                self._use_optimized = True
                self.logger.info(f"Initialized optimized event system at {self.optimization_level} level")
            except Exception as e:
                self.logger.error(f"Failed to initialize optimized event system: {e}")
                self._use_optimized = False
        
        # Initialize fallback system if needed
        if self.fallback_enabled and (not self._use_optimized or self.optimization_level == OptimizationLevel.DISABLED):
            try:
                from .event_proxy import EventBridgeCoordinator
                self._fallback_coordinator = EventBridgeCoordinator()
                if not self._use_optimized:
                    self.logger.info("Using fallback event coordinator")
            except Exception as e:
                self.logger.error(f"Failed to initialize fallback coordinator: {e}")
    
    def start(self) -> bool:
        """Start the event coordination system"""
        if self._is_active:
            return True
        
        success = False
        
        # Try to start optimized system first
        if self._use_optimized and self._optimized_bridge:
            try:
                self._optimized_bridge.start()
                success = True
                self.logger.info("Started optimized event system")
            except Exception as e:
                self.logger.error(f"Failed to start optimized system: {e}")
                self._use_optimized = False
        
        # Fallback to legacy coordinator if needed
        if not success and self._fallback_coordinator:
            try:
                # Legacy coordinator may not have start method
                if hasattr(self._fallback_coordinator, 'start'):
                    self._fallback_coordinator.start()
                success = True
                self.logger.info("Started fallback event coordinator")
            except Exception as e:
                self.logger.error(f"Failed to start fallback coordinator: {e}")
        
        self._is_active = success
        return success
    
    def stop(self) -> None:
        """Stop the event coordination system"""
        if not self._is_active:
            return
        
        # Stop optimized system
        if self._optimized_bridge:
            try:
                self._optimized_bridge.stop()
            except Exception as e:
                self.logger.error(f"Error stopping optimized system: {e}")
        
        # Stop fallback system
        if self._fallback_coordinator:
            try:
                if hasattr(self._fallback_coordinator, 'stop'):
                    self._fallback_coordinator.stop()
            except Exception as e:
                self.logger.error(f"Error stopping fallback coordinator: {e}")
        
        self._is_active = False
        self.logger.info("Stopped event coordination system")
    
    def emit_event(self, event_type: Union[str, EventType], source: str = "adapter", 
                   data: Any = None, priority: str = "normal") -> bool:
        """
        Emit an event with automatic routing to optimized or fallback system
        
        Args:
            event_type: Event type (string or EventType enum)
            source: Event source identifier
            data: Event payload data
            priority: Event priority (normal, high, critical)
            
        Returns:
            bool: True if event was successfully emitted
        """
        if not self._is_active:
            self.logger.warning("Event coordinator not active")
            return False
        
        # Convert string event type to EventType enum if needed
        if isinstance(event_type, str):
            try:
                event_type = EventType[event_type.upper()]
            except (KeyError, AttributeError):
                self.logger.warning(f"Unknown event type: {event_type}")
                event_type = EventType.DATA_UPDATED  # Default fallback
        
        # Convert priority string to EventPriority enum
        priority_mapping = {
            "critical": EventPriority.CRITICAL,
            "high": EventPriority.HIGH,
            "normal": EventPriority.NORMAL,
            "low": EventPriority.LOW,
            "background": EventPriority.BACKGROUND
        }
        event_priority = priority_mapping.get(priority.lower(), EventPriority.NORMAL)
        
        # Try optimized system first
        if self._use_optimized and self._optimized_bridge:
            try:
                success = self._optimized_bridge.emit_event(
                    event_type=event_type,
                    source=source,
                    data=data,
                    priority=event_priority
                )
                if success:
                    return True
                else:
                    self.logger.debug("Optimized system rejected event, trying fallback")
            except Exception as e:
                self.logger.error(f"Error in optimized system: {e}")
                # Fall through to fallback
        
        # Try fallback system
        if self._fallback_coordinator:
            try:
                # Create Event object for fallback system
                event = Event(
                    event_type=event_type,
                    source=source,
                    data=data,
                    timestamp=time.time()
                )
                
                # Emit through fallback (method signature may vary)
                if hasattr(self._fallback_coordinator, 'emit_event'):
                    return self._fallback_coordinator.emit_event(event)
                elif hasattr(self._fallback_coordinator, 'dispatch_event'):
                    return self._fallback_coordinator.dispatch_event(event)
                else:
                    self.logger.warning("Fallback coordinator has no emit method")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error in fallback system: {e}")
                return False
        
        self.logger.error("No working event system available")
        return False
    
    def register_handler(self, event_type: Union[str, EventType], 
                        handler: Callable, priority: int = 0) -> Optional[str]:
        """
        Register an event handler
        
        Args:
            event_type: Event type to listen for
            handler: Callback function
            priority: Handler priority (higher = called first)
            
        Returns:
            str: Handler ID for unregistration, or None if failed
        """
        # Convert string event type to EventType enum if needed
        if isinstance(event_type, str):
            try:
                event_type = EventType[event_type.upper()]
            except (KeyError, AttributeError):
                self.logger.warning(f"Unknown event type: {event_type}")
                return None
        
        # Try optimized system first
        if self._use_optimized and self._optimized_bridge:
            try:
                handler_id = self._optimized_bridge.register_handler(event_type, handler)
                if handler_id:
                    return handler_id
            except Exception as e:
                self.logger.error(f"Error registering handler in optimized system: {e}")
        
        # Try fallback system
        if self._fallback_coordinator:
            try:
                if hasattr(self._fallback_coordinator, 'register_handler'):
                    return self._fallback_coordinator.register_handler(event_type, handler, priority)
                elif hasattr(self._fallback_coordinator, 'add_listener'):
                    return self._fallback_coordinator.add_listener(event_type, handler)
            except Exception as e:
                self.logger.error(f"Error registering handler in fallback system: {e}")
        
        return None
    
    def unregister_handler(self, handler_id: str) -> bool:
        """
        Unregister an event handler
        
        Args:
            handler_id: Handler ID returned from register_handler
            
        Returns:
            bool: True if successfully unregistered
        """
        success = False
        
        # Try optimized system
        if self._use_optimized and self._optimized_bridge:
            try:
                success = self._optimized_bridge.unregister_handler(handler_id)
                if success:
                    return True
            except Exception as e:
                self.logger.error(f"Error unregistering handler in optimized system: {e}")
        
        # Try fallback system
        if self._fallback_coordinator:
            try:
                if hasattr(self._fallback_coordinator, 'unregister_handler'):
                    success = self._fallback_coordinator.unregister_handler(handler_id)
                elif hasattr(self._fallback_coordinator, 'remove_listener'):
                    success = self._fallback_coordinator.remove_listener(handler_id)
            except Exception as e:
                self.logger.error(f"Error unregistering handler in fallback system: {e}")
        
        return success
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        metrics = {
            "system_info": {
                "optimization_level": self.optimization_level,
                "using_optimized": self._use_optimized,
                "using_fallback": self._fallback_coordinator is not None,
                "is_active": self._is_active
            },
            "performance": {},
            "timestamp": time.time()
        }
        
        # Get optimized system metrics
        if self._use_optimized and self._optimized_bridge:
            try:
                opt_metrics = self._optimized_bridge.get_performance_metrics()
                metrics["performance"] = opt_metrics
            except Exception as e:
                self.logger.error(f"Error getting optimized metrics: {e}")
        
        # Store metrics history if enabled
        if self.metrics_enabled:
            with self._metrics_lock:
                self._metrics_history.append(metrics.copy())
                # Keep only last 100 entries
                if len(self._metrics_history) > 100:
                    self._metrics_history = self._metrics_history[-100:]
        
        return metrics
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """Get historical performance metrics"""
        with self._metrics_lock:
            return self._metrics_history.copy()
    
    def benchmark_performance(self, num_events: int = 1000) -> Dict[str, float]:
        """
        Run a performance benchmark
        
        Args:
            num_events: Number of test events to process
            
        Returns:
            dict: Benchmark results
        """
        if not self._is_active:
            return {"error": "System not active"}
        
        # Use optimized benchmark if available
        if self._use_optimized and self._optimized_bridge:
            try:
                return self._optimized_bridge.benchmark_performance(num_events)
            except Exception as e:
                self.logger.error(f"Optimized benchmark failed: {e}")
        
        # Fallback to simple benchmark
        start_time = time.time()
        success_count = 0
        
        for i in range(num_events):
            success = self.emit_event(
                event_type="DATA_UPDATED",
                source="benchmark",
                data={"test_id": i, "timestamp": time.time()}
            )
            if success:
                success_count += 1
        
        duration = time.time() - start_time
        
        return {
            "duration_seconds": duration,
            "events_submitted": num_events,
            "events_processed": success_count,
            "throughput_events_per_second": num_events / duration if duration > 0 else 0,
            "processing_efficiency": (success_count / num_events * 100) if num_events > 0 else 0,
            "system": "fallback"
        }
    
    def switch_optimization_level(self, new_level: str) -> bool:
        """
        Switch to a different optimization level
        
        Args:
            new_level: New optimization level
            
        Returns:
            bool: True if successfully switched
        """
        if new_level not in self._performance_configs:
            self.logger.error(f"Invalid optimization level: {new_level}")
            return False
        
        was_active = self._is_active
        
        # Stop current system
        if was_active:
            self.stop()
        
        # Update configuration
        self.optimization_level = new_level
        self.config["optimization_level"] = new_level
        
        # Reinitialize systems
        self._initialize_systems()
        
        # Restart if it was active before
        if was_active:
            return self.start()
        
        return True
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration"""
        return {
            "optimization_level": self.optimization_level,
            "fallback_enabled": self.fallback_enabled,
            "metrics_enabled": self.metrics_enabled,
            "performance_config": self._performance_configs.get(self.optimization_level, {}),
            "system_status": {
                "optimized_available": OPTIMIZER_AVAILABLE,
                "using_optimized": self._use_optimized,
                "is_active": self._is_active
            }
        }
    
    def save_configuration(self, filepath: str) -> bool:
        """Save configuration to file"""
        try:
            config = self.export_configuration()
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False


# Global coordinator instance
_global_coordinator: Optional[OptimizedEventCoordinator] = None
_coordinator_lock = Lock()


def get_optimized_coordinator(config: Optional[Dict[str, Any]] = None) -> OptimizedEventCoordinator:
    """
    Get the global optimized event coordinator instance
    
    Args:
        config: Optional configuration dict
        
    Returns:
        OptimizedEventCoordinator: Global coordinator instance
    """
    global _global_coordinator
    
    with _coordinator_lock:
        if _global_coordinator is None:
            _global_coordinator = OptimizedEventCoordinator(config)
        return _global_coordinator


def initialize_optimized_events(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Initialize the optimized event system globally
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: True if successfully initialized
    """
    coordinator = get_optimized_coordinator(config)
    return coordinator.start()


def shutdown_optimized_events() -> None:
    """Shutdown the optimized event system"""
    global _global_coordinator
    
    with _coordinator_lock:
        if _global_coordinator:
            _global_coordinator.stop()
            _global_coordinator = None


# Backward compatibility functions
def get_global_coordinator():
    """Backward compatibility: Get global coordinator"""
    return get_optimized_coordinator()


def emit_adapter_event(event_type: str, source: str = "adapter", data: Any = None) -> bool:
    """Backward compatibility: Emit adapter event"""
    coordinator = get_optimized_coordinator()
    return coordinator.emit_event(event_type, source, data)


def register_adapter_handler(event_type: str, handler: Callable) -> Optional[str]:
    """Backward compatibility: Register adapter handler"""
    coordinator = get_optimized_coordinator()
    return coordinator.register_handler(event_type, handler) 