"""
Network Optimization and Connection Management Framework
======================================================

This module provides comprehensive network optimization for Social Download Manager v2.0.
Includes connection pooling, request optimization, bandwidth management, DNS caching,
adaptive timeout strategies, and network quality monitoring.

Key Features:
- HTTP connection pooling with keepalive and session reuse
- Intelligent bandwidth management with rate limiting
- DNS resolution caching and optimization
- Adaptive timeout strategies based on network conditions
- Network quality monitoring and adjustment
- Request header optimization for maximum compatibility
"""

import asyncio
import aiohttp
import time
import dns.resolver
import socket
from typing import Dict, List, Optional, Tuple, Callable, Union, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import logging
import ssl
import threading
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class NetworkMetrics:
    """Metrics for network operations."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_bytes_downloaded: int = 0
    average_download_speed: float = 0.0  # MB/s
    average_response_time: float = 0.0   # seconds
    connection_pool_hits: int = 0
    connection_pool_misses: int = 0
    dns_cache_hits: int = 0
    dns_cache_misses: int = 0
    timeout_count: int = 0
    retry_count: int = 0

@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pooling."""
    max_connections: int = 100
    max_connections_per_host: int = 10
    keepalive_timeout: int = 30
    timeout_total: float = 300.0
    timeout_connect: float = 10.0
    timeout_sock_read: float = 30.0
    enable_compression: bool = True
    trust_env: bool = True

@dataclass
class BandwidthConfig:
    """Configuration for bandwidth management."""
    max_download_rate: Optional[float] = None  # MB/s, None = unlimited
    burst_rate: Optional[float] = None         # MB/s for burst downloads
    burst_duration: float = 10.0               # seconds
    rate_limit_window: float = 1.0             # seconds for rate limiting

@dataclass
class NetworkQuality:
    """Network quality assessment."""
    latency_ms: float = 0.0
    bandwidth_mbps: float = 0.0
    packet_loss_percent: float = 0.0
    jitter_ms: float = 0.0
    quality_score: float = 0.0  # 0-100 scale
    last_updated: float = 0.0

class DNSCache:
    """DNS resolution cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
        
    def get(self, hostname: str) -> Optional[str]:
        """Get cached DNS resolution."""
        with self.lock:
            if hostname in self.cache:
                ip, expiry = self.cache[hostname]
                if time.time() < expiry:
                    return ip
                else:
                    # Expired entry
                    del self.cache[hostname]
        return None
    
    def set(self, hostname: str, ip: str, ttl: Optional[int] = None):
        """Cache DNS resolution."""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        with self.lock:
            self.cache[hostname] = (ip, expiry)
    
    def clear_expired(self):
        """Clear expired DNS entries."""
        current_time = time.time()
        with self.lock:
            expired_keys = [k for k, (_, expiry) in self.cache.items() if current_time >= expiry]
            for key in expired_keys:
                del self.cache[key]
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self.lock:
            return {
                "total_entries": len(self.cache),
                "expired_entries": sum(1 for _, expiry in self.cache.values() if time.time() >= expiry)
            }

class BandwidthLimiter:
    """Bandwidth limiting with token bucket algorithm."""
    
    def __init__(self, config: BandwidthConfig):
        self.config = config
        self.tokens = config.max_download_rate or float('inf')
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        
    async def acquire(self, bytes_count: int) -> float:
        """Acquire tokens for bytes, return delay if needed."""
        if not self.config.max_download_rate:
            return 0.0
            
        async with self.lock:
            current_time = time.time()
            time_passed = current_time - self.last_update
            
            # Refill tokens
            tokens_to_add = self.config.max_download_rate * time_passed * 1024 * 1024  # Convert MB/s to bytes/s
            self.tokens = min(self.config.max_download_rate * 1024 * 1024, self.tokens + tokens_to_add)
            self.last_update = current_time
            
            # Check if we have enough tokens
            if bytes_count <= self.tokens:
                self.tokens -= bytes_count
                return 0.0
            else:
                # Calculate delay needed
                deficit = bytes_count - self.tokens
                delay = deficit / (self.config.max_download_rate * 1024 * 1024)
                self.tokens = 0
                return delay

class NetworkQualityMonitor:
    """Monitor and assess network quality."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.latencies = deque(maxlen=window_size)
        self.bandwidths = deque(maxlen=window_size)
        self.last_assessment = NetworkQuality()
        
    async def ping_test(self, host: str, timeout: float = 5.0) -> float:
        """Perform ping test to measure latency."""
        try:
            start_time = time.time()
            
            # Use aiohttp for HTTP ping (more reliable than ICMP)
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.head(f"http://{host}", allow_redirects=False) as response:
                    latency = (time.time() - start_time) * 1000  # Convert to ms
                    self.latencies.append(latency)
                    return latency
                    
        except Exception as e:
            logger.warning(f"Ping test failed for {host}: {e}")
            # Return high latency on failure
            latency = timeout * 1000
            self.latencies.append(latency)
            return latency
    
    def record_bandwidth(self, bytes_transferred: int, duration: float):
        """Record bandwidth measurement."""
        if duration > 0:
            bandwidth_mbps = (bytes_transferred / duration) / (1024 * 1024)
            self.bandwidths.append(bandwidth_mbps)
    
    def get_quality_assessment(self) -> NetworkQuality:
        """Get current network quality assessment."""
        if not self.latencies and not self.bandwidths:
            return self.last_assessment
            
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 100.0
        avg_bandwidth = sum(self.bandwidths) / len(self.bandwidths) if self.bandwidths else 1.0
        
        # Calculate jitter (latency variation)
        jitter = 0.0
        if len(self.latencies) > 1:
            mean_latency = avg_latency
            jitter = sum(abs(l - mean_latency) for l in self.latencies) / len(self.latencies)
        
        # Calculate quality score (0-100)
        # Lower latency is better, higher bandwidth is better, lower jitter is better
        latency_score = max(0, 100 - (avg_latency / 10))  # 100ms = 90 points, 1000ms = 0 points
        bandwidth_score = min(100, avg_bandwidth * 10)    # 10 MB/s = 100 points
        jitter_score = max(0, 100 - (jitter / 5))         # 500ms jitter = 0 points
        
        quality_score = (latency_score + bandwidth_score + jitter_score) / 3
        
        self.last_assessment = NetworkQuality(
            latency_ms=avg_latency,
            bandwidth_mbps=avg_bandwidth,
            packet_loss_percent=0.0,  # Would need additional testing
            jitter_ms=jitter,
            quality_score=quality_score,
            last_updated=time.time()
        )
        
        return self.last_assessment

class AdaptiveTimeoutManager:
    """Manage adaptive timeouts based on network conditions."""
    
    def __init__(self, base_timeout: float = 30.0):
        self.base_timeout = base_timeout
        self.timeout_history = deque(maxlen=20)
        self.success_rate = 1.0
        
    def get_timeout(self, network_quality: NetworkQuality) -> float:
        """Get adaptive timeout based on network quality."""
        # Base timeout adjustment based on latency
        latency_factor = 1.0 + (network_quality.latency_ms / 1000.0)  # Add 1s per 1000ms latency
        
        # Adjust based on quality score
        quality_factor = 2.0 - (network_quality.quality_score / 100.0)  # 1.0x for perfect, 2.0x for poor
        
        # Adjust based on recent success rate
        success_factor = 2.0 - self.success_rate  # 1.0x for 100% success, 2.0x for 0% success
        
        adaptive_timeout = self.base_timeout * latency_factor * quality_factor * success_factor
        
        # Clamp to reasonable bounds
        return max(5.0, min(300.0, adaptive_timeout))
    
    def record_result(self, success: bool, duration: float):
        """Record request result for adaptive learning."""
        self.timeout_history.append((success, duration))
        
        # Update success rate
        if self.timeout_history:
            recent_successes = sum(1 for success, _ in self.timeout_history if success)
            self.success_rate = recent_successes / len(self.timeout_history)

class OptimizedHTTPClient:
    """Optimized HTTP client with connection pooling and advanced features."""
    
    def __init__(self, config: ConnectionPoolConfig, bandwidth_config: BandwidthConfig):
        self.config = config
        self.bandwidth_config = bandwidth_config
        self.session = None
        self.dns_cache = DNSCache()
        self.bandwidth_limiter = BandwidthLimiter(bandwidth_config)
        self.quality_monitor = NetworkQualityMonitor()
        self.timeout_manager = AdaptiveTimeoutManager()
        self.metrics = NetworkMetrics()
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Initialize the HTTP client."""
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create connector with optimized settings
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections_per_host,
            keepalive_timeout=self.config.keepalive_timeout,
            enable_cleanup_closed=True,
            ssl=ssl_context,
            use_dns_cache=True,
            ttl_dns_cache=300
        )
        
        # Create session with optimized settings
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout_total,
            connect=self.config.timeout_connect,
            sock_read=self.config.timeout_sock_read
        )
        
        headers = {
            'User-Agent': 'Social-Download-Manager/2.0 (Optimized)',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate' if self.config.enable_compression else 'identity',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        }
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            trust_env=self.config.trust_env
        )
    
    async def close(self):
        """Close the HTTP client."""
        if self.session:
            await self.session.close()
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Optimized GET request."""
        return await self._request('GET', url, **kwargs)
    
    async def head(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Optimized HEAD request."""
        return await self._request('HEAD', url, **kwargs)
    
    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Internal optimized request method."""
        if not self.session:
            await self.start()
        
        start_time = time.time()
        
        try:
            # Get network quality and adaptive timeout
            quality = self.quality_monitor.get_quality_assessment()
            adaptive_timeout = self.timeout_manager.get_timeout(quality)
            
            # Override timeout if not specified
            if 'timeout' not in kwargs:
                kwargs['timeout'] = aiohttp.ClientTimeout(total=adaptive_timeout)
            
            # Perform DNS resolution with caching
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname
            
            cached_ip = self.dns_cache.get(hostname)
            if cached_ip:
                self.metrics.dns_cache_hits += 1
            else:
                # Resolve DNS and cache it
                try:
                    resolved_ip = socket.gethostbyname(hostname)
                    self.dns_cache.set(hostname, resolved_ip)
                    self.metrics.dns_cache_misses += 1
                except socket.gaierror:
                    # DNS resolution failed, continue with original hostname
                    self.metrics.dns_cache_misses += 1
            
            # Make the request
            async with self.session.request(method, url, **kwargs) as response:
                duration = time.time() - start_time
                
                # Update metrics
                self.metrics.total_requests += 1
                if response.status < 400:
                    self.metrics.successful_requests += 1
                    self.timeout_manager.record_result(True, duration)
                else:
                    self.metrics.failed_requests += 1
                    self.timeout_manager.record_result(False, duration)
                
                # Update response time
                if self.metrics.total_requests > 0:
                    self.metrics.average_response_time = (
                        (self.metrics.average_response_time * (self.metrics.total_requests - 1) + duration) / 
                        self.metrics.total_requests
                    )
                
                return response
                
        except asyncio.TimeoutError:
            self.metrics.timeout_count += 1
            self.metrics.failed_requests += 1
            self.timeout_manager.record_result(False, time.time() - start_time)
            raise
        except Exception as e:
            self.metrics.failed_requests += 1
            self.timeout_manager.record_result(False, time.time() - start_time)
            raise
    
    async def download_with_progress(self, url: str, progress_callback: Optional[Callable] = None,
                                   chunk_size: int = 8192) -> bytes:
        """Download with progress tracking and bandwidth limiting."""
        start_time = time.time()
        downloaded_data = bytearray()
        
        async with self.get(url) as response:
            if response.status >= 400:
                raise aiohttp.ClientError(f"HTTP {response.status}: {response.reason}")
            
            total_size = int(response.headers.get('Content-Length', 0))
            bytes_downloaded = 0
            
            async for chunk in response.content.iter_chunked(chunk_size):
                # Apply bandwidth limiting
                delay = await self.bandwidth_limiter.acquire(len(chunk))
                if delay > 0:
                    await asyncio.sleep(delay)
                
                downloaded_data.extend(chunk)
                bytes_downloaded += len(chunk)
                
                # Update progress
                if progress_callback:
                    progress_callback(bytes_downloaded, total_size)
            
            # Update metrics
            duration = time.time() - start_time
            if duration > 0:
                speed_mbps = (bytes_downloaded / duration) / (1024 * 1024)
                self.quality_monitor.record_bandwidth(bytes_downloaded, duration)
                
                # Update average download speed
                if self.metrics.total_bytes_downloaded > 0:
                    self.metrics.average_download_speed = (
                        (self.metrics.average_download_speed * self.metrics.total_bytes_downloaded + 
                         speed_mbps * bytes_downloaded) / (self.metrics.total_bytes_downloaded + bytes_downloaded)
                    )
                else:
                    self.metrics.average_download_speed = speed_mbps
                
                self.metrics.total_bytes_downloaded += bytes_downloaded
        
        return bytes(downloaded_data)
    
    def get_metrics(self) -> NetworkMetrics:
        """Get current network metrics."""
        return self.metrics
    
    def get_network_quality(self) -> NetworkQuality:
        """Get current network quality assessment."""
        return self.quality_monitor.get_quality_assessment()

class NetworkOptimizer:
    """Main network optimization coordinator."""
    
    def __init__(self, connection_config: Optional[ConnectionPoolConfig] = None,
                 bandwidth_config: Optional[BandwidthConfig] = None):
        self.connection_config = connection_config or ConnectionPoolConfig()
        self.bandwidth_config = bandwidth_config or BandwidthConfig()
        self.http_client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = OptimizedHTTPClient(self.connection_config, self.bandwidth_config)
        await self.http_client.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.close()
    
    async def optimize_connection(self, url: str) -> Dict[str, Any]:
        """Optimize connection for a specific URL."""
        if not self.http_client:
            self.http_client = OptimizedHTTPClient(self.connection_config, self.bandwidth_config)
            await self.http_client.start()
        
        # Test connection and measure performance
        start_time = time.time()
        
        try:
            async with self.http_client.head(url) as response:
                duration = time.time() - start_time
                
                return {
                    "status": "success",
                    "response_time": duration,
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "connection_optimized": True
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "response_time": time.time() - start_time,
                "connection_optimized": False
            }
    
    async def benchmark_network(self, test_urls: List[str]) -> Dict[str, Any]:
        """Benchmark network performance with test URLs."""
        if not self.http_client:
            self.http_client = OptimizedHTTPClient(self.connection_config, self.bandwidth_config)
            await self.http_client.start()
        
        results = {}
        
        for url in test_urls:
            try:
                # Ping test
                parsed_url = urlparse(url)
                hostname = parsed_url.hostname
                latency = await self.http_client.quality_monitor.ping_test(hostname)
                
                # Download test (small file)
                start_time = time.time()
                async with self.http_client.get(url) as response:
                    content = await response.read()
                    duration = time.time() - start_time
                    
                    if duration > 0:
                        speed_mbps = (len(content) / duration) / (1024 * 1024)
                    else:
                        speed_mbps = 0.0
                
                results[url] = {
                    "latency_ms": latency,
                    "download_speed_mbps": speed_mbps,
                    "content_size": len(content),
                    "status": "success"
                }
                
            except Exception as e:
                results[url] = {
                    "error": str(e),
                    "status": "failed"
                }
        
        return results
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        if not self.http_client:
            return {"error": "HTTP client not initialized"}
        
        metrics = self.http_client.get_metrics()
        quality = self.http_client.get_network_quality()
        dns_stats = self.http_client.dns_cache.get_stats()
        
        return {
            "network_metrics": {
                "total_requests": metrics.total_requests,
                "success_rate": (metrics.successful_requests / metrics.total_requests * 100) 
                               if metrics.total_requests > 0 else 0,
                "average_download_speed_mbps": metrics.average_download_speed,
                "average_response_time": metrics.average_response_time,
                "total_data_downloaded_mb": metrics.total_bytes_downloaded / (1024 * 1024)
            },
            "connection_pooling": {
                "hits": metrics.connection_pool_hits,
                "misses": metrics.connection_pool_misses,
                "hit_rate": (metrics.connection_pool_hits / 
                           (metrics.connection_pool_hits + metrics.connection_pool_misses) * 100)
                           if (metrics.connection_pool_hits + metrics.connection_pool_misses) > 0 else 0
            },
            "dns_cache": {
                "hits": metrics.dns_cache_hits,
                "misses": metrics.dns_cache_misses,
                "hit_rate": (metrics.dns_cache_hits / 
                           (metrics.dns_cache_hits + metrics.dns_cache_misses) * 100)
                           if (metrics.dns_cache_hits + metrics.dns_cache_misses) > 0 else 0,
                "total_entries": dns_stats["total_entries"]
            },
            "network_quality": {
                "latency_ms": quality.latency_ms,
                "bandwidth_mbps": quality.bandwidth_mbps,
                "jitter_ms": quality.jitter_ms,
                "quality_score": quality.quality_score
            },
            "timeouts_and_retries": {
                "timeout_count": metrics.timeout_count,
                "retry_count": metrics.retry_count
            }
        }

# Demo and testing functions
async def demo_network_optimization():
    """Demonstrate network optimization capabilities."""
    print("🌐 Network Optimization Demo")
    print("=" * 50)
    
    # Configuration
    connection_config = ConnectionPoolConfig(
        max_connections=50,
        max_connections_per_host=5,
        keepalive_timeout=60
    )
    
    bandwidth_config = BandwidthConfig(
        max_download_rate=10.0,  # 10 MB/s limit
        burst_rate=20.0,         # 20 MB/s burst
        burst_duration=5.0       # 5 second burst
    )
    
    async with NetworkOptimizer(connection_config, bandwidth_config) as optimizer:
        # Test connection optimization
        test_url = "https://httpbin.org/get"
        print(f"\n🔗 Testing Connection Optimization:")
        print(f"  URL: {test_url}")
        
        connection_result = await optimizer.optimize_connection(test_url)
        print(f"  Status: {connection_result['status']}")
        print(f"  Response Time: {connection_result['response_time']:.3f}s")
        
        if connection_result['status'] == 'success':
            print(f"  Status Code: {connection_result['status_code']}")
            print(f"  Connection Optimized: ✅")
        
        # Benchmark multiple URLs
        test_urls = [
            "https://httpbin.org/json",
            "https://httpbin.org/html",
            "https://httpbin.org/xml"
        ]
        
        print(f"\n📊 Network Benchmarking:")
        benchmark_results = await optimizer.benchmark_network(test_urls)
        
        for url, result in benchmark_results.items():
            print(f"  {url}:")
            if result['status'] == 'success':
                print(f"    Latency: {result['latency_ms']:.1f}ms")
                print(f"    Speed: {result['download_speed_mbps']:.2f} MB/s")
                print(f"    Size: {result['content_size']} bytes")
            else:
                print(f"    Error: {result['error']}")
        
        # Get optimization report
        print(f"\n📈 Optimization Report:")
        report = optimizer.get_optimization_report()
        
        print(f"  Network Metrics:")
        print(f"    Total Requests: {report['network_metrics']['total_requests']}")
        print(f"    Success Rate: {report['network_metrics']['success_rate']:.1f}%")
        print(f"    Avg Response Time: {report['network_metrics']['average_response_time']:.3f}s")
        
        print(f"  DNS Cache:")
        print(f"    Hit Rate: {report['dns_cache']['hit_rate']:.1f}%")
        print(f"    Total Entries: {report['dns_cache']['total_entries']}")
        
        print(f"  Network Quality:")
        print(f"    Quality Score: {report['network_quality']['quality_score']:.1f}/100")
        print(f"    Latency: {report['network_quality']['latency_ms']:.1f}ms")
    
    print(f"\n✅ Network optimization demo completed!")

if __name__ == "__main__":
    asyncio.run(demo_network_optimization()) 