#!/usr/bin/env python3
"""
Network Optimization Test Runner
===============================

Comprehensive testing suite for Social Download Manager v2.0 network optimizations.
Tests connection pooling, bandwidth management, DNS caching, adaptive timeouts,
and network quality monitoring.

Usage:
    python run_network_optimization.py [--mode=MODE] [--timeout=SECONDS]

Modes:
    all         - Run all optimization tests (default)
    connection  - Test connection pooling only
    bandwidth   - Test bandwidth management only
    dns         - Test DNS caching only
    quality     - Test network quality monitoring only
    adaptive    - Test adaptive timeouts only
    demo        - Run interactive demonstration
"""

import os
import sys
import time
import asyncio
import argparse
from typing import Dict, List, Any

# Add scripts directory to path for imports
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts', 'performance')
sys.path.insert(0, scripts_dir)

try:
    from network_optimizer import (
        NetworkOptimizer, OptimizedHTTPClient, DNSCache, 
        BandwidthLimiter, NetworkQualityMonitor, AdaptiveTimeoutManager,
        ConnectionPoolConfig, BandwidthConfig, NetworkMetrics
    )
except ImportError as e:
    print(f"❌ Error importing network optimizer: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install aiohttp dnspython")
    sys.exit(1)

class NetworkTestRunner:
    """Comprehensive network optimization test runner."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.results = {}
        
    async def test_connection_pooling(self) -> Dict[str, Any]:
        """Test HTTP connection pooling optimization."""
        print("\n🔗 Phase 1: Connection Pooling Optimization")
        print("-" * 45)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Test with different pool configurations
            configs = [
                ConnectionPoolConfig(max_connections=10, max_connections_per_host=2),
                ConnectionPoolConfig(max_connections=50, max_connections_per_host=5),
                ConnectionPoolConfig(max_connections=100, max_connections_per_host=10),
            ]
            
            test_urls = [
                "https://httpbin.org/get",
                "https://httpbin.org/json",
                "https://httpbin.org/user-agent"
            ]
            
            for i, config in enumerate(configs):
                print(f"  Config {i+1}: {config.max_connections} max, {config.max_connections_per_host} per host")
                
                bandwidth_config = BandwidthConfig()
                async with OptimizedHTTPClient(config, bandwidth_config) as client:
                    start_time = time.time()
                    
                    # Make multiple concurrent requests
                    tasks = []
                    for url in test_urls:
                        for _ in range(3):  # 3 requests per URL
                            tasks.append(client.get(url))
                    
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    duration = time.time() - start_time
                    
                    # Count successful responses
                    successful = sum(1 for r in responses if not isinstance(r, Exception))
                    metrics = client.get_metrics()
                    
                    print(f"    Requests: {len(tasks)}, Success: {successful}, Time: {duration:.2f}s")
                    print(f"    Avg Response: {metrics.average_response_time:.3f}s")
                    
                    results["details"][f"config_{i+1}"] = {
                        "total_requests": len(tasks),
                        "successful_requests": successful,
                        "duration": duration,
                        "avg_response_time": metrics.average_response_time,
                        "success_rate": (successful / len(tasks)) * 100
                    }
                    
                    if successful < len(tasks) * 0.8:  # 80% success threshold
                        results["errors"].append(f"Low success rate for config {i+1}: {successful}/{len(tasks)}")
            
            print(f"✅ Connection pooling tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Connection pooling failed: {e}")
        
        return results
    
    async def test_bandwidth_management(self) -> Dict[str, Any]:
        """Test bandwidth management and rate limiting."""
        print("\n📡 Phase 2: Bandwidth Management")
        print("-" * 35)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Test different bandwidth limits
            bandwidth_configs = [
                BandwidthConfig(max_download_rate=1.0),   # 1 MB/s
                BandwidthConfig(max_download_rate=5.0),   # 5 MB/s
                BandwidthConfig(max_download_rate=None),  # Unlimited
            ]
            
            connection_config = ConnectionPoolConfig()
            
            for i, bw_config in enumerate(bandwidth_configs):
                limit_str = f"{bw_config.max_download_rate} MB/s" if bw_config.max_download_rate else "Unlimited"
                print(f"  Testing bandwidth limit: {limit_str}")
                
                async with OptimizedHTTPClient(connection_config, bw_config) as client:
                    # Test download with progress tracking
                    test_url = "https://httpbin.org/drip?numbytes=100000&duration=1"  # 100KB over 1 second
                    
                    progress_updates = []
                    def track_progress(bytes_downloaded, total_bytes):
                        progress_updates.append((time.time(), bytes_downloaded))
                    
                    start_time = time.time()
                    try:
                        data = await client.download_with_progress(test_url, track_progress)
                        duration = time.time() - start_time
                        
                        if data:
                            actual_speed = (len(data) / duration) / (1024 * 1024)  # MB/s
                            print(f"    Downloaded: {len(data)} bytes in {duration:.2f}s")
                            print(f"    Actual speed: {actual_speed:.2f} MB/s")
                            
                            results["details"][f"bandwidth_test_{i+1}"] = {
                                "limit_mbps": bw_config.max_download_rate,
                                "actual_speed_mbps": actual_speed,
                                "duration": duration,
                                "bytes_downloaded": len(data),
                                "progress_updates": len(progress_updates)
                            }
                            
                            # Check if rate limiting is working
                            if bw_config.max_download_rate and actual_speed > bw_config.max_download_rate * 1.5:
                                results["errors"].append(f"Rate limiting not working: {actual_speed:.2f} > {bw_config.max_download_rate}")
                        
                    except Exception as e:
                        print(f"    Download failed: {e}")
                        results["details"][f"bandwidth_test_{i+1}"] = {"error": str(e)}
            
            print(f"✅ Bandwidth management tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Bandwidth management failed: {e}")
        
        return results
    
    async def test_dns_caching(self) -> Dict[str, Any]:
        """Test DNS caching functionality."""
        print("\n🌐 Phase 3: DNS Caching")
        print("-" * 25)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            dns_cache = DNSCache(default_ttl=60)
            
            # Test hostnames
            test_hosts = [
                "httpbin.org",
                "google.com", 
                "github.com"
            ]
            
            print(f"  Testing DNS resolution and caching:")
            
            for host in test_hosts:
                # First resolution (cache miss)
                start_time = time.time()
                first_ip = dns_cache.get(host)
                if first_ip is None:
                    # Resolve and cache
                    import socket
                    try:
                        resolved_ip = socket.gethostbyname(host)
                        dns_cache.set(host, resolved_ip)
                        first_resolution_time = time.time() - start_time
                        print(f"    {host} → {resolved_ip} ({first_resolution_time*1000:.1f}ms)")
                        
                        # Second resolution (cache hit)
                        start_time = time.time()
                        cached_ip = dns_cache.get(host)
                        cache_resolution_time = time.time() - start_time
                        
                        if cached_ip == resolved_ip:
                            print(f"    Cache hit: {host} → {cached_ip} ({cache_resolution_time*1000:.3f}ms)")
                            
                            results["details"][host] = {
                                "ip": resolved_ip,
                                "first_resolution_ms": first_resolution_time * 1000,
                                "cache_resolution_ms": cache_resolution_time * 1000,
                                "cache_speedup": first_resolution_time / cache_resolution_time if cache_resolution_time > 0 else float('inf')
                            }
                        else:
                            results["errors"].append(f"Cache miss for {host}: {cached_ip} != {resolved_ip}")
                            
                    except socket.gaierror as e:
                        print(f"    {host} → DNS resolution failed: {e}")
                        results["details"][host] = {"error": str(e)}
            
            # Test cache statistics
            cache_stats = dns_cache.get_stats()
            print(f"  Cache stats: {cache_stats['total_entries']} entries")
            
            results["details"]["cache_stats"] = cache_stats
            
            print(f"✅ DNS caching tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ DNS caching failed: {e}")
        
        return results
    
    async def test_network_quality_monitoring(self) -> Dict[str, Any]:
        """Test network quality monitoring."""
        print("\n📊 Phase 4: Network Quality Monitoring")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            quality_monitor = NetworkQualityMonitor(window_size=5)
            
            test_hosts = ["httpbin.org", "google.com"]
            
            print(f"  Testing network quality assessment:")
            
            for host in test_hosts:
                print(f"    Testing {host}:")
                
                # Perform multiple ping tests
                latencies = []
                for i in range(3):
                    latency = await quality_monitor.ping_test(host, timeout=5.0)
                    latencies.append(latency)
                    print(f"      Ping {i+1}: {latency:.1f}ms")
                
                # Record some bandwidth measurements
                for i in range(3):
                    # Simulate bandwidth measurement
                    bytes_transferred = 1024 * 1024 * (i + 1)  # 1MB, 2MB, 3MB
                    duration = 1.0 + (i * 0.1)  # Varying durations
                    quality_monitor.record_bandwidth(bytes_transferred, duration)
                
                # Get quality assessment
                quality = quality_monitor.get_quality_assessment()
                
                print(f"      Quality Score: {quality.quality_score:.1f}/100")
                print(f"      Avg Latency: {quality.latency_ms:.1f}ms")
                print(f"      Avg Bandwidth: {quality.bandwidth_mbps:.2f} MB/s")
                print(f"      Jitter: {quality.jitter_ms:.1f}ms")
                
                results["details"][host] = {
                    "latencies": latencies,
                    "avg_latency": quality.latency_ms,
                    "bandwidth_mbps": quality.bandwidth_mbps,
                    "jitter_ms": quality.jitter_ms,
                    "quality_score": quality.quality_score
                }
                
                # Validate quality score is reasonable
                if quality.quality_score < 0 or quality.quality_score > 100:
                    results["errors"].append(f"Invalid quality score for {host}: {quality.quality_score}")
            
            print(f"✅ Network quality monitoring tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Network quality monitoring failed: {e}")
        
        return results
    
    async def test_adaptive_timeouts(self) -> Dict[str, Any]:
        """Test adaptive timeout management."""
        print("\n⏱️ Phase 5: Adaptive Timeout Management")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            timeout_manager = AdaptiveTimeoutManager(base_timeout=30.0)
            
            # Create mock network quality scenarios
            quality_scenarios = [
                {"name": "Perfect Network", "latency": 10.0, "quality": 95.0},
                {"name": "Good Network", "latency": 50.0, "quality": 80.0},
                {"name": "Poor Network", "latency": 200.0, "quality": 40.0},
                {"name": "Very Poor Network", "latency": 1000.0, "quality": 10.0},
            ]
            
            print(f"  Testing adaptive timeout calculation:")
            
            for scenario in quality_scenarios:
                # Create mock network quality
                from network_optimizer import NetworkQuality
                quality = NetworkQuality(
                    latency_ms=scenario["latency"],
                    quality_score=scenario["quality"],
                    last_updated=time.time()
                )
                
                # Get adaptive timeout
                adaptive_timeout = timeout_manager.get_timeout(quality)
                
                print(f"    {scenario['name']}:")
                print(f"      Latency: {scenario['latency']:.1f}ms")
                print(f"      Quality: {scenario['quality']:.1f}/100")
                print(f"      Adaptive Timeout: {adaptive_timeout:.1f}s")
                
                results["details"][scenario["name"]] = {
                    "latency_ms": scenario["latency"],
                    "quality_score": scenario["quality"],
                    "adaptive_timeout": adaptive_timeout
                }
                
                # Validate timeout is reasonable
                if adaptive_timeout < 5.0 or adaptive_timeout > 300.0:
                    results["errors"].append(f"Unreasonable timeout for {scenario['name']}: {adaptive_timeout}s")
                
                # Test recording results
                timeout_manager.record_result(True, adaptive_timeout * 0.5)  # Successful request
            
            # Test with some failures
            print(f"    Testing failure adaptation:")
            for _ in range(3):
                timeout_manager.record_result(False, 30.0)  # Failed requests
            
            # Get timeout after failures
            poor_quality = NetworkQuality(latency_ms=100.0, quality_score=50.0)
            timeout_after_failures = timeout_manager.get_timeout(poor_quality)
            
            print(f"      Timeout after failures: {timeout_after_failures:.1f}s")
            results["details"]["failure_adaptation"] = {
                "timeout_after_failures": timeout_after_failures,
                "success_rate": timeout_manager.success_rate
            }
            
            print(f"✅ Adaptive timeout tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Adaptive timeout failed: {e}")
        
        return results
    
    async def test_integrated_performance(self) -> Dict[str, Any]:
        """Test integrated network optimization performance."""
        print("\n🚀 Phase 6: Integrated Performance Test")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Test with full optimization
            connection_config = ConnectionPoolConfig(
                max_connections=20,
                max_connections_per_host=5,
                keepalive_timeout=30
            )
            
            bandwidth_config = BandwidthConfig(
                max_download_rate=None  # No limit for testing
            )
            
            async with NetworkOptimizer(connection_config, bandwidth_config) as optimizer:
                # Test multiple URLs concurrently
                test_urls = [
                    "https://httpbin.org/get",
                    "https://httpbin.org/json",
                    "https://httpbin.org/user-agent",
                    "https://httpbin.org/headers"
                ]
                
                print(f"  Testing integrated optimization with {len(test_urls)} URLs:")
                
                start_time = time.time()
                
                # Run connection tests
                connection_tasks = [optimizer.optimize_connection(url) for url in test_urls]
                connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
                
                total_duration = time.time() - start_time
                
                successful_connections = sum(1 for r in connection_results 
                                           if not isinstance(r, Exception) and r.get('status') == 'success')
                
                print(f"    Connections: {successful_connections}/{len(test_urls)} successful")
                print(f"    Total time: {total_duration:.2f}s")
                print(f"    Avg time per connection: {total_duration/len(test_urls):.3f}s")
                
                # Get comprehensive report
                report = optimizer.get_optimization_report()
                
                print(f"  Optimization Report:")
                print(f"    Success Rate: {report['network_metrics']['success_rate']:.1f}%")
                print(f"    Avg Response Time: {report['network_metrics']['average_response_time']:.3f}s")
                print(f"    DNS Cache Hit Rate: {report['dns_cache']['hit_rate']:.1f}%")
                
                results["details"]["integrated_test"] = {
                    "successful_connections": successful_connections,
                    "total_connections": len(test_urls),
                    "total_duration": total_duration,
                    "avg_duration_per_connection": total_duration / len(test_urls),
                    "success_rate": (successful_connections / len(test_urls)) * 100,
                    "optimization_report": report
                }
                
                # Validate performance
                if successful_connections < len(test_urls) * 0.8:  # 80% success threshold
                    results["errors"].append(f"Low success rate: {successful_connections}/{len(test_urls)}")
                
                if total_duration > 30.0:  # Should complete within 30 seconds
                    results["errors"].append(f"Performance too slow: {total_duration:.2f}s")
            
            print(f"✅ Integrated performance tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Integrated performance test failed: {e}")
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all network optimization tests."""
        print("🌐 Starting Network Optimization Tests")
        print("=" * 50)
        
        all_results = {}
        
        # Run all test phases
        test_phases = [
            ("connection_pooling", self.test_connection_pooling),
            ("bandwidth_management", self.test_bandwidth_management),
            ("dns_caching", self.test_dns_caching),
            ("network_quality_monitoring", self.test_network_quality_monitoring),
            ("adaptive_timeouts", self.test_adaptive_timeouts),
            ("integrated_performance", self.test_integrated_performance)
        ]
        
        passed_count = 0
        
        for phase_name, test_func in test_phases:
            try:
                result = await test_func()
                all_results[phase_name] = result
                
                if result["status"] == "PASSED":
                    passed_count += 1
                    
            except Exception as e:
                all_results[phase_name] = {
                    "status": "FAILED",
                    "errors": [str(e)],
                    "details": {}
                }
        
        # Summary
        print(f"\n📋 Network Optimization Test Summary")
        print("=" * 50)
        print(f"✅ Passed: {passed_count}/{len(test_phases)} phases")
        
        if passed_count == len(test_phases):
            print("🎉 ALL NETWORK TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - check details above")
        
        return all_results

async def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Network Optimization Test Runner")
    parser.add_argument("--mode", choices=["all", "connection", "bandwidth", "dns", "quality", "adaptive", "demo"], 
                       default="all", help="Test mode to run")
    parser.add_argument("--timeout", type=float, default=30.0, help="Test timeout in seconds")
    
    args = parser.parse_args()
    
    runner = NetworkTestRunner(timeout=args.timeout)
    
    try:
        if args.mode == "demo":
            # Run demo from the module
            from network_optimizer import demo_network_optimization
            await demo_network_optimization()
        else:
            # Run tests based on mode
            if args.mode == "all":
                await runner.run_all_tests()
            elif args.mode == "connection":
                await runner.test_connection_pooling()
            elif args.mode == "bandwidth":
                await runner.test_bandwidth_management()
            elif args.mode == "dns":
                await runner.test_dns_caching()
            elif args.mode == "quality":
                await runner.test_network_quality_monitoring()
            elif args.mode == "adaptive":
                await runner.test_adaptive_timeouts()
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 