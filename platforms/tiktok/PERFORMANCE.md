# TikTok Handler Performance Guide

This document provides comprehensive guidance on optimizing performance, monitoring metrics, and tuning the TikTok platform handler for various use cases.

## Table of Contents

- [Performance Overview](#performance-overview)
- [Optimization Techniques](#optimization-techniques)
- [Benchmarking Guide](#benchmarking-guide)
- [Performance Monitoring](#performance-monitoring)
- [Tuning Recommendations](#tuning-recommendations)
- [Common Performance Issues](#common-performance-issues)
- [Best Practices](#best-practices)

## Performance Overview

The TikTok handler is designed with performance as a primary consideration, utilizing multiple optimization strategies to achieve high throughput and low latency.

### Key Performance Metrics

| Metric | Typical Value | Target Value |
|--------|---------------|--------------|
| Video Info Retrieval | 2-5 seconds | < 3 seconds |
| Cache Hit Response | 50-200ms | < 100ms |
| Concurrent Operations | 5-10 simultaneous | 10+ simultaneous |
| Memory Usage | 50-200MB | < 150MB |
| Download Speed | Network dependent | 80% of bandwidth |

### Performance Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│               Enhanced Handler                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │    Cache    │ │  Task Pool  │ │  Connection     │   │
│  │   System    │ │   Manager   │ │    Pool         │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Base TikTok Handler                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │    Error    │ │   Session   │ │   Rate Limit    │   │
│  │  Handling   │ │ Management  │ │    Control      │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                 yt-dlp Integration                      │
└─────────────────────────────────────────────────────────┘
```

## Optimization Techniques

### 1. Caching Optimization

#### Multi-Level Caching

```python
# High-performance caching configuration
cache_config = {
    'enable_caching': True,
    'cache_ttl': 3600,  # 1 hour for production
    'cache_max_size': 5000,  # Larger cache
    'cache_types': {
        'video_info': {'enabled': True, 'ttl': 1800},
        'format_selection': {'enabled': True, 'ttl': 3600},
        'metadata_extraction': {'enabled': True, 'ttl': 1800},
        'upload_date_parsing': {'enabled': True, 'ttl': 86400}
    }
}
```

#### Cache Hit Rate Optimization

```python
def optimize_cache_hit_rate():
    """Strategies to improve cache hit rates"""
    
    # 1. URL Normalization
    def normalize_url(url: str) -> str:
        # Remove tracking parameters
        # Standardize URL format
        # Convert mobile URLs to standard format
        pass
    
    # 2. Intelligent Cache Keys
    def generate_cache_key(url: str, context: dict) -> str:
        # Include relevant context in key generation
        # Use consistent hashing algorithms
        # Consider parameter ordering
        pass
    
    # 3. Cache Warming
    async def warm_cache(popular_urls: List[str]):
        # Pre-load frequently accessed content
        # Background cache refresh
        # Predictive caching based on patterns
        pass
```

### 2. Concurrency Optimization

#### Async Task Pool Configuration

```python
# Optimal concurrency configuration
concurrency_config = {
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 10,  # Adjust based on system resources
    'max_concurrent_downloads': 3,    # Limit to avoid overwhelming servers
    'max_concurrent_metadata_extractions': 15,
    'task_queue_size': 100,
    'worker_timeout': 300  # 5 minutes
}

# Usage example
async def process_multiple_videos(urls: List[str]):
    """Process multiple videos concurrently with optimal configuration"""
    
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(10)
    
    async def process_with_semaphore(url):
        async with semaphore:
            return await handler.get_video_info(url)
    
    # Execute with controlled concurrency
    tasks = [process_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

#### Connection Pool Optimization

```python
# Connection pool settings for high performance
connection_config = {
    'connection_pool_size': 20,      # Increase for high concurrency
    'max_connections_per_host': 10,  # Balance load across connections
    'connection_timeout': 30,        # Reasonable timeout
    'read_timeout': 60,              # Allow for large downloads
    'keep_alive': True,              # Reuse connections
    'keep_alive_timeout': 30,        # Connection persistence
    'retry_attempts': 3,             # Resilience for transient errors
    'retry_backoff': 1.0            # Exponential backoff
}
```

### 3. Memory Optimization

#### Memory-Efficient Processing

```python
# Memory optimization configuration
memory_config = {
    'lazy_loading': True,           # Load data on demand
    'batch_size': 100,              # Process in smaller batches
    'max_memory_usage': 512,        # 512MB limit
    'garbage_collection': {
        'enabled': True,
        'interval': 300,            # 5 minutes
        'threshold': 0.8           # Trigger at 80% usage
    },
    'streaming_threshold': 10485760  # 10MB - stream larger files
}

# Memory monitoring example
class MemoryMonitor:
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory = max_memory_mb * 1024 * 1024
        
    def check_memory_usage(self):
        """Monitor and manage memory usage"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        if memory_info.rss > self.max_memory:
            # Trigger garbage collection
            import gc
            gc.collect()
            
            # Clear caches if still over limit
            if memory_info.rss > self.max_memory:
                self.clear_caches()
```

### 4. Network Optimization

#### Request Optimization

```python
# Network optimization settings
network_config = {
    'user_agent_rotation': True,
    'connection_reuse': True,
    'compression': True,
    'headers_optimization': {
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'application/json, text/plain, */*',
        'Connection': 'keep-alive'
    },
    'dns_caching': True,
    'tcp_keepalive': True
}

# Request batching for efficiency
async def batch_requests(urls: List[str], batch_size: int = 5):
    """Process URLs in optimized batches"""
    
    results = []
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        
        # Process batch concurrently
        batch_results = await asyncio.gather(*[
            handler.get_video_info(url) for url in batch
        ], return_exceptions=True)
        
        results.extend(batch_results)
        
        # Small delay between batches for rate limiting
        if i + batch_size < len(urls):
            await asyncio.sleep(1)
    
    return results
```

## Benchmarking Guide

### 1. Performance Testing Setup

```python
import time
import asyncio
import statistics
from typing import List, Dict

class PerformanceBenchmark:
    def __init__(self, handler):
        self.handler = handler
        self.results = []
        
    async def benchmark_video_info(self, urls: List[str], runs: int = 5):
        """Benchmark video information retrieval"""
        
        for run in range(runs):
            print(f"Run {run + 1}/{runs}")
            run_results = []
            
            for url in urls:
                start_time = time.time()
                try:
                    video_info = await self.handler.get_video_info(url)
                    duration = time.time() - start_time
                    run_results.append({
                        'url': url,
                        'duration': duration,
                        'success': True,
                        'title': video_info.title
                    })
                except Exception as e:
                    duration = time.time() - start_time
                    run_results.append({
                        'url': url,
                        'duration': duration,
                        'success': False,
                        'error': str(e)
                    })
            
            self.results.append(run_results)
            
            # Cool-down between runs
            await asyncio.sleep(2)
    
    def generate_report(self) -> Dict:
        """Generate performance report"""
        
        all_durations = []
        success_count = 0
        total_requests = 0
        
        for run in self.results:
            for result in run:
                all_durations.append(result['duration'])
                total_requests += 1
                if result['success']:
                    success_count += 1
        
        return {
            'total_requests': total_requests,
            'success_rate': success_count / total_requests * 100,
            'avg_duration': statistics.mean(all_durations),
            'median_duration': statistics.median(all_durations),
            'min_duration': min(all_durations),
            'max_duration': max(all_durations),
            'std_deviation': statistics.stdev(all_durations) if len(all_durations) > 1 else 0
        }

# Usage example
async def run_benchmark():
    # Test URLs (replace with actual URLs)
    test_urls = [
        "https://www.tiktok.com/@user1/video/1111111111111111111",
        "https://www.tiktok.com/@user2/video/2222222222222222222",
        "https://www.tiktok.com/@user3/video/3333333333333333333"
    ]
    
    # Standard handler benchmark
    standard_handler = TikTokHandler()
    standard_benchmark = PerformanceBenchmark(standard_handler)
    await standard_benchmark.benchmark_video_info(test_urls)
    standard_report = standard_benchmark.generate_report()
    
    # Enhanced handler benchmark
    enhanced_handler = EnhancedTikTokHandler({'enable_caching': True})
    enhanced_benchmark = PerformanceBenchmark(enhanced_handler)
    await enhanced_benchmark.benchmark_video_info(test_urls)
    enhanced_report = enhanced_benchmark.generate_report()
    
    # Compare results
    print(f"Standard Handler - Avg: {standard_report['avg_duration']:.2f}s")
    print(f"Enhanced Handler - Avg: {enhanced_report['avg_duration']:.2f}s")
    print(f"Performance Improvement: {(1 - enhanced_report['avg_duration'] / standard_report['avg_duration']) * 100:.1f}%")
```

### 2. Load Testing

```python
class LoadTest:
    def __init__(self, handler, max_concurrent: int = 10):
        self.handler = handler
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def simulate_load(self, urls: List[str], duration_seconds: int = 60):
        """Simulate load for specified duration"""
        
        start_time = time.time()
        results = []
        request_count = 0
        
        async def make_request():
            nonlocal request_count
            async with self.semaphore:
                url = urls[request_count % len(urls)]
                request_count += 1
                
                start = time.time()
                try:
                    await self.handler.get_video_info(url)
                    duration = time.time() - start
                    return {'success': True, 'duration': duration}
                except Exception as e:
                    duration = time.time() - start
                    return {'success': False, 'duration': duration, 'error': str(e)}
        
        # Generate load
        tasks = []
        while time.time() - start_time < duration_seconds:
            task = asyncio.create_task(make_request())
            tasks.append(task)
            
            # Control request rate
            await asyncio.sleep(0.1)  # 10 requests per second
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate load test metrics
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
        total_time = time.time() - start_time
        
        return {
            'total_requests': len(results),
            'successful_requests': successful,
            'requests_per_second': len(results) / total_time,
            'success_rate': successful / len(results) * 100,
            'test_duration': total_time
        }
```

## Performance Monitoring

### 1. Real-Time Monitoring

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'response_times': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_usage': [],
            'concurrent_operations': 0
        }
        self.start_time = time.time()
    
    def record_request(self, duration: float, success: bool, cache_hit: bool = False):
        """Record request metrics"""
        self.metrics['requests_total'] += 1
        self.metrics['response_times'].append(duration)
        
        if success:
            self.metrics['requests_successful'] += 1
        else:
            self.metrics['requests_failed'] += 1
            
        if cache_hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
    
    def get_current_stats(self) -> Dict:
        """Get current performance statistics"""
        uptime = time.time() - self.start_time
        
        response_times = self.metrics['response_times']
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (self.metrics['cache_hits'] / cache_total * 100) if cache_total > 0 else 0
        
        return {
            'uptime': uptime,
            'requests_per_second': self.metrics['requests_total'] / uptime,
            'success_rate': (self.metrics['requests_successful'] / self.metrics['requests_total'] * 100) if self.metrics['requests_total'] > 0 else 0,
            'avg_response_time': avg_response_time,
            'cache_hit_rate': cache_hit_rate,
            'total_requests': self.metrics['requests_total']
        }
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        stats = self.get_current_stats()
        
        return f"""
# HELP tiktok_requests_total Total number of requests
# TYPE tiktok_requests_total counter
tiktok_requests_total {self.metrics['requests_total']}

# HELP tiktok_requests_per_second Current requests per second
# TYPE tiktok_requests_per_second gauge
tiktok_requests_per_second {stats['requests_per_second']:.2f}

# HELP tiktok_success_rate Success rate percentage
# TYPE tiktok_success_rate gauge
tiktok_success_rate {stats['success_rate']:.2f}

# HELP tiktok_avg_response_time Average response time in seconds
# TYPE tiktok_avg_response_time gauge
tiktok_avg_response_time {stats['avg_response_time']:.3f}

# HELP tiktok_cache_hit_rate Cache hit rate percentage
# TYPE tiktok_cache_hit_rate gauge
tiktok_cache_hit_rate {stats['cache_hit_rate']:.2f}
"""
```

### 2. Performance Alerting

```python
class PerformanceAlerting:
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.thresholds = {
            'response_time_warning': 5.0,      # 5 seconds
            'response_time_critical': 10.0,    # 10 seconds
            'success_rate_warning': 95.0,      # 95%
            'success_rate_critical': 90.0,     # 90%
            'cache_hit_rate_warning': 70.0,    # 70%
            'memory_usage_warning': 80.0       # 80%
        }
    
    def check_alerts(self) -> List[Dict]:
        """Check for performance alerts"""
        alerts = []
        stats = self.monitor.get_current_stats()
        
        # Response time alerts
        if stats['avg_response_time'] > self.thresholds['response_time_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'metric': 'response_time',
                'value': stats['avg_response_time'],
                'threshold': self.thresholds['response_time_critical'],
                'message': f"Average response time is {stats['avg_response_time']:.2f}s (critical threshold: {self.thresholds['response_time_critical']}s)"
            })
        elif stats['avg_response_time'] > self.thresholds['response_time_warning']:
            alerts.append({
                'level': 'WARNING',
                'metric': 'response_time',
                'value': stats['avg_response_time'],
                'threshold': self.thresholds['response_time_warning'],
                'message': f"Average response time is {stats['avg_response_time']:.2f}s (warning threshold: {self.thresholds['response_time_warning']}s)"
            })
        
        # Success rate alerts
        if stats['success_rate'] < self.thresholds['success_rate_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'metric': 'success_rate',
                'value': stats['success_rate'],
                'threshold': self.thresholds['success_rate_critical'],
                'message': f"Success rate is {stats['success_rate']:.1f}% (critical threshold: {self.thresholds['success_rate_critical']}%)"
            })
        elif stats['success_rate'] < self.thresholds['success_rate_warning']:
            alerts.append({
                'level': 'WARNING',
                'metric': 'success_rate',
                'value': stats['success_rate'],
                'threshold': self.thresholds['success_rate_warning'],
                'message': f"Success rate is {stats['success_rate']:.1f}% (warning threshold: {self.thresholds['success_rate_warning']}%)"
            })
        
        # Cache hit rate alerts
        if stats['cache_hit_rate'] < self.thresholds['cache_hit_rate_warning']:
            alerts.append({
                'level': 'WARNING',
                'metric': 'cache_hit_rate',
                'value': stats['cache_hit_rate'],
                'threshold': self.thresholds['cache_hit_rate_warning'],
                'message': f"Cache hit rate is {stats['cache_hit_rate']:.1f}% (warning threshold: {self.thresholds['cache_hit_rate_warning']}%)"
            })
        
        return alerts
```

## Tuning Recommendations

### 1. Environment-Based Tuning

#### Development Environment

```python
development_config = {
    'enable_caching': True,
    'cache_ttl': 300,                    # 5 minutes
    'cache_max_size': 100,               # Small cache
    'enable_concurrent_processing': False, # Easier debugging
    'max_concurrent_operations': 2,       # Low concurrency
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 30,        # Conservative
        'min_request_interval': 2.0
    },
    'logging': {
        'level': 'DEBUG',
        'enable_performance_logging': True
    }
}
```

#### Production Environment

```python
production_config = {
    'enable_caching': True,
    'cache_ttl': 3600,                   # 1 hour
    'cache_max_size': 5000,              # Large cache
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 15,      # High concurrency
    'connection_pool_size': 25,
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 180,       # Aggressive but safe
        'adaptive_limiting': True,
        'circuit_breaker': {
            'enabled': True,
            'failure_threshold': 100,
            'recovery_timeout': 1800
        }
    },
    'memory_config': {
        'max_memory_usage': 1024,         # 1GB
        'garbage_collection': {
            'enabled': True,
            'interval': 180               # 3 minutes
        }
    }
}
```

#### High-Load Environment

```python
high_load_config = {
    'enable_caching': True,
    'cache_ttl': 7200,                   # 2 hours
    'cache_max_size': 10000,             # Very large cache
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 25,      # Very high concurrency
    'connection_pool_size': 50,
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 300,       # Maximum sustainable rate
        'adaptive_limiting': True,
        'burst_limit': 50,
        'circuit_breaker': {
            'enabled': True,
            'failure_threshold': 200,
            'recovery_timeout': 3600
        }
    },
    'memory_config': {
        'max_memory_usage': 2048,         # 2GB
        'garbage_collection': {
            'enabled': True,
            'interval': 120               # 2 minutes
        }
    }
}
```

### 2. Hardware-Based Recommendations

#### CPU Optimization

```python
# For CPU-bound workloads
cpu_optimized_config = {
    'enable_concurrent_processing': True,
    'max_concurrent_operations': min(32, os.cpu_count() * 2),
    'task_queue_size': 200,
    'worker_timeout': 180,
    'memory_config': {
        'lazy_loading': True,
        'batch_size': 50
    }
}
```

#### Memory Optimization

```python
# For memory-constrained environments
memory_optimized_config = {
    'cache_max_size': 500,               # Smaller cache
    'enable_concurrent_processing': False, # Reduce memory pressure
    'memory_config': {
        'max_memory_usage': 256,         # 256MB limit
        'garbage_collection': {
            'enabled': True,
            'interval': 60,              # Frequent cleanup
            'threshold': 0.7             # Lower threshold
        },
        'streaming_threshold': 5242880   # 5MB - stream smaller files
    }
}
```

#### Network Optimization

```python
# For network-constrained environments
network_optimized_config = {
    'connection_pool_size': 5,           # Fewer connections
    'max_concurrent_operations': 3,      # Lower concurrency
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 60,       # Conservative rate
        'min_request_interval': 1.5,
        'adaptive_limiting': True
    },
    'connection_config': {
        'connection_timeout': 60,        # Longer timeouts
        'read_timeout': 120,
        'retry_attempts': 5,
        'retry_backoff': 2.0
    }
}
```

## Common Performance Issues

### 1. Cache Miss Rates

**Symptoms**:
- High response times
- Repeated identical requests
- Low cache hit rates

**Diagnosis**:
```python
def diagnose_cache_issues(handler):
    """Diagnose cache-related performance issues"""
    
    cache_stats = handler.get_cache_statistics()
    
    issues = []
    
    if cache_stats.get('hit_rate', 0) < 50:
        issues.append({
            'issue': 'Low cache hit rate',
            'current_value': cache_stats.get('hit_rate', 0),
            'recommendations': [
                'Increase cache TTL',
                'Optimize cache key generation',
                'Pre-warm cache with popular content'
            ]
        })
    
    if cache_stats.get('cache_size', 0) > cache_stats.get('max_size', 1000) * 0.9:
        issues.append({
            'issue': 'Cache near capacity',
            'current_value': cache_stats.get('cache_size', 0),
            'recommendations': [
                'Increase cache max size',
                'Implement better eviction strategy',
                'Monitor cache usage patterns'
            ]
        })
    
    return issues
```

**Solutions**:
- Increase cache TTL for stable content
- Implement cache warming strategies
- Optimize cache key generation
- Increase cache size limits

### 2. Rate Limiting Issues

**Symptoms**:
- Frequent rate limit errors
- Circuit breaker activation
- Degraded performance

**Diagnosis**:
```python
def diagnose_rate_limiting(handler):
    """Diagnose rate limiting issues"""
    
    error_stats = handler.get_error_statistics()
    rate_limit_errors = error_stats.get('rate_limit_errors', 0)
    total_errors = error_stats.get('total_errors', 0)
    
    if rate_limit_errors > total_errors * 0.1:  # >10% rate limit errors
        return {
            'issue': 'High rate limiting',
            'rate_limit_percentage': (rate_limit_errors / total_errors * 100) if total_errors > 0 else 0,
            'recommendations': [
                'Reduce requests per minute',
                'Increase request intervals',
                'Implement better backoff strategy',
                'Enable adaptive rate limiting'
            ]
        }
    
    return None
```

**Solutions**:
- Reduce request rates
- Implement exponential backoff
- Use adaptive rate limiting
- Distribute load across multiple instances

### 3. Memory Leaks

**Symptoms**:
- Gradually increasing memory usage
- Out of memory errors
- Performance degradation over time

**Diagnosis**:
```python
import psutil
import gc

def diagnose_memory_issues():
    """Diagnose memory-related issues"""
    
    process = psutil.Process()
    memory_info = process.memory_info()
    
    # Check for memory growth patterns
    memory_mb = memory_info.rss / 1024 / 1024
    
    issues = []
    
    if memory_mb > 500:  # >500MB
        issues.append({
            'issue': 'High memory usage',
            'current_value': f"{memory_mb:.1f}MB",
            'recommendations': [
                'Enable garbage collection',
                'Reduce cache size',
                'Implement memory monitoring',
                'Use streaming for large files'
            ]
        })
    
    # Check garbage collection stats
    gc_stats = gc.get_stats()
    for i, stat in enumerate(gc_stats):
        if stat['uncollectable'] > 0:
            issues.append({
                'issue': f'Uncollectable objects in generation {i}',
                'current_value': stat['uncollectable'],
                'recommendations': [
                    'Review object lifecycle management',
                    'Check for circular references',
                    'Implement proper resource cleanup'
                ]
            })
    
    return issues
```

**Solutions**:
- Enable automatic garbage collection
- Implement proper resource cleanup
- Use context managers for resources
- Monitor memory usage patterns

## Best Practices

### 1. Configuration Best Practices

```python
def get_optimal_config(environment: str, resources: Dict) -> Dict:
    """Get optimal configuration based on environment and resources"""
    
    base_config = {
        'enable_caching': True,
        'enable_concurrent_processing': True,
        'rate_limit': {'enabled': True}
    }
    
    # Adjust based on available CPU cores
    cpu_cores = resources.get('cpu_cores', 2)
    base_config['max_concurrent_operations'] = min(20, cpu_cores * 2)
    
    # Adjust based on available memory
    memory_mb = resources.get('memory_mb', 1024)
    base_config['cache_max_size'] = min(10000, memory_mb // 2)
    
    # Environment-specific adjustments
    if environment == 'development':
        base_config.update({
            'cache_ttl': 300,
            'rate_limit': {'requests_per_minute': 30}
        })
    elif environment == 'production':
        base_config.update({
            'cache_ttl': 3600,
            'rate_limit': {'requests_per_minute': 120}
        })
    elif environment == 'high_load':
        base_config.update({
            'cache_ttl': 7200,
            'rate_limit': {'requests_per_minute': 240}
        })
    
    return base_config
```

### 2. Monitoring Best Practices

```python
# Set up comprehensive monitoring
def setup_monitoring(handler):
    """Set up comprehensive performance monitoring"""
    
    # Performance monitor
    monitor = PerformanceMonitor()
    
    # Alerting system
    alerting = PerformanceAlerting(monitor)
    
    # Regular health checks
    async def health_check():
        while True:
            alerts = alerting.check_alerts()
            for alert in alerts:
                print(f"[{alert['level']}] {alert['message']}")
            
            await asyncio.sleep(60)  # Check every minute
    
    # Start monitoring
    asyncio.create_task(health_check())
    
    return monitor
```

### 3. Testing Best Practices

```python
# Regular performance testing
async def regular_performance_test():
    """Run regular performance tests"""
    
    test_urls = get_test_urls()
    
    # Test different configurations
    configs = [
        ('baseline', {}),
        ('optimized', get_optimized_config()),
        ('high_performance', get_high_performance_config())
    ]
    
    for config_name, config in configs:
        handler = TikTokHandler(config)
        benchmark = PerformanceBenchmark(handler)
        
        await benchmark.benchmark_video_info(test_urls)
        report = benchmark.generate_report()
        
        print(f"{config_name}: {report['avg_duration']:.2f}s avg, {report['success_rate']:.1f}% success")
```

### 4. Optimization Checklist

- [ ] Enable caching with appropriate TTL values
- [ ] Configure optimal concurrency levels
- [ ] Implement proper error handling and recovery
- [ ] Set up performance monitoring and alerting
- [ ] Regularly benchmark performance
- [ ] Monitor memory usage and implement cleanup
- [ ] Use connection pooling for better network efficiency
- [ ] Implement rate limiting to avoid service restrictions
- [ ] Test configuration changes in staging environment
- [ ] Document performance baselines and expectations

By following this performance guide, you can optimize the TikTok handler for your specific use case and maintain high performance under various load conditions. 