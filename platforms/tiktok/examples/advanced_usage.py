#!/usr/bin/env python3
"""
Advanced TikTok Handler Usage Examples

This example demonstrates advanced features of the TikTok handler:
- Performance optimization with enhanced handler
- Concurrent downloads and processing
- Advanced error handling and recovery
- Custom progress tracking
- Performance monitoring and statistics

Requirements:
- pip install yt-dlp
- Proper project structure with platforms.tiktok module
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from platforms.tiktok import TikTokHandler
from platforms.tiktok.enhanced_handler import EnhancedTikTokHandler
from platforms.tiktok.performance_optimizations import (
    TikTokPerformanceCache,
    PerformanceMonitor,
    AsyncTaskPool
)


class AdvancedProgressTracker:
    """Advanced progress tracking with statistics"""
    
    def __init__(self):
        self.downloads = {}
        self.start_times = {}
        self.completed = 0
        self.failed = 0
        
    def start_download(self, url: str):
        """Start tracking a download"""
        self.downloads[url] = {
            'status': 'starting',
            'progress': 0,
            'speed': 0,
            'eta': None,
            'total_bytes': None,
            'downloaded_bytes': 0
        }
        self.start_times[url] = time.time()
        
    def update_progress(self, url: str, info: Dict[str, Any]):
        """Update download progress"""
        if url not in self.downloads:
            return
            
        status = info.get('status', 'unknown')
        self.downloads[url]['status'] = status
        
        if status == 'downloading':
            self.downloads[url].update({
                'progress': info.get('_percent_str', '0%'),
                'speed': info.get('_speed_str', '0 B/s'),
                'eta': info.get('_eta_str', 'Unknown'),
                'total_bytes': info.get('total_bytes'),
                'downloaded_bytes': info.get('downloaded_bytes', 0)
            })
        elif status == 'finished':
            self.downloads[url]['status'] = 'completed'
            self.completed += 1
        elif status == 'error':
            self.downloads[url]['status'] = 'failed'
            self.failed += 1
            
    def get_summary(self) -> Dict[str, Any]:
        """Get download summary statistics"""
        total = len(self.downloads)
        in_progress = sum(1 for d in self.downloads.values() if d['status'] == 'downloading')
        
        return {
            'total': total,
            'completed': self.completed,
            'failed': self.failed,
            'in_progress': in_progress,
            'success_rate': (self.completed / total * 100) if total > 0 else 0
        }


async def enhanced_handler_example():
    """Example: Using the enhanced handler with performance optimizations"""
    print("=" * 60)
    print("ENHANCED HANDLER EXAMPLE")
    print("=" * 60)
    
    # Initialize enhanced handler with aggressive optimization
    config = {
        'enable_caching': True,
        'cache_ttl': 3600,  # 1 hour cache
        'cache_max_size': 5000,
        'enable_concurrent_processing': True,
        'max_concurrent_operations': 10,
        'connection_pool_size': 20,
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 120,
            'adaptive_limiting': True
        }
    }
    
    enhanced_handler = EnhancedTikTokHandler(config=config)
    
    print("🚀 Enhanced handler initialized with optimizations")
    
    # Test URLs
    test_urls = [
        "https://www.tiktok.com/@user1/video/1111111111111111111",
        "https://www.tiktok.com/@user2/video/2222222222222222222",
        "https://www.tiktok.com/@user3/video/3333333333333333333"
    ]
    
    print(f"📋 Testing with {len(test_urls)} URLs")
    
    # Measure performance
    start_time = time.time()
    
    try:
        # Concurrent video info retrieval
        print("🔍 Retrieving video information concurrently...")
        
        async def get_video_info_with_timing(url):
            info_start = time.time()
            try:
                video_info = await enhanced_handler.get_video_info(url)
                duration = time.time() - info_start
                return url, video_info, duration, None
            except Exception as e:
                duration = time.time() - info_start
                return url, None, duration, str(e)
        
        # Execute concurrently
        results = await asyncio.gather(*[
            get_video_info_with_timing(url) for url in test_urls
        ], return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Process results
        successful = 0
        total_duration = 0
        
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Task failed: {result}")
                continue
                
            url, video_info, duration, error = result
            total_duration += duration
            
            if error:
                print(f"❌ {url}: {error} (took {duration:.2f}s)")
            else:
                successful += 1
                print(f"✅ {url}: {video_info.title[:50]}... (took {duration:.2f}s)")
        
        # Performance statistics
        print(f"\n📊 Performance Statistics:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average per request: {total_duration/len(test_urls):.2f}s")
        print(f"   Success rate: {successful}/{len(test_urls)} ({successful/len(test_urls)*100:.1f}%)")
        print(f"   Concurrent speedup: {(total_duration/total_time):.1f}x")
        
        # Cache statistics
        cache_stats = enhanced_handler.get_cache_statistics()
        if cache_stats:
            print(f"📈 Cache Statistics:")
            print(f"   Cache size: {cache_stats.get('cache_size', 0)}")
            print(f"   Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
            
    except Exception as e:
        print(f"❌ Enhanced handler example failed: {e}")


async def concurrent_download_example():
    """Example: Concurrent video downloads with progress tracking"""
    print("\n" + "=" * 60)
    print("CONCURRENT DOWNLOAD EXAMPLE")
    print("=" * 60)
    
    # Initialize handler for downloads
    config = {
        'enable_caching': True,
        'enable_concurrent_processing': True,
        'max_concurrent_operations': 3,  # Limit concurrent downloads
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 60
        }
    }
    
    handler = TikTokHandler(config=config)
    progress_tracker = AdvancedProgressTracker()
    
    # Download URLs
    download_urls = [
        "https://www.tiktok.com/@user1/video/1111111111111111111",
        "https://www.tiktok.com/@user2/video/2222222222222222222",
        "https://www.tiktok.com/@user3/video/3333333333333333333",
        "https://www.tiktok.com/@user4/video/4444444444444444444"
    ]
    
    # Create download directory
    download_dir = Path("downloads/concurrent_examples")
    download_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 Download directory: {download_dir.absolute()}")
    print(f"🔗 Downloading {len(download_urls)} videos concurrently")
    
    async def download_with_tracking(url: str, index: int):
        """Download a single video with progress tracking"""
        try:
            progress_tracker.start_download(url)
            
            def progress_callback(info):
                progress_tracker.update_progress(url, info)
                if info.get('status') == 'downloading':
                    progress = info.get('_percent_str', '0%')
                    speed = info.get('_speed_str', '0 B/s')
                    print(f"📥 Video {index+1}: {progress} at {speed}")
            
            download_options = {
                'output_path': str(download_dir),
                'quality_preference': 'HD',
                'include_audio': True,
                'progress_callback': progress_callback,
                'filename_template': f'video_{index+1}_%(title)s.%(ext)s'
            }
            
            print(f"🚀 Starting download {index+1}...")
            result = await handler.download_video(url, download_options)
            
            if result.success:
                print(f"✅ Download {index+1} completed: {result.file_path}")
                return index, result, None
            else:
                print(f"❌ Download {index+1} failed: {result.error_message}")
                return index, None, result.error_message
                
        except Exception as e:
            print(f"❌ Download {index+1} error: {e}")
            progress_tracker.update_progress(url, {'status': 'error'})
            return index, None, str(e)
    
    # Execute concurrent downloads
    start_time = time.time()
    
    try:
        # Use semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(3)
        
        async def download_with_semaphore(url, index):
            async with semaphore:
                return await download_with_tracking(url, index)
        
        results = await asyncio.gather(*[
            download_with_semaphore(url, i) 
            for i, url in enumerate(download_urls)
        ], return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Process results
        successful_downloads = 0
        total_size = 0
        
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Download task failed: {result}")
                continue
                
            index, download_result, error = result
            if download_result and download_result.success:
                successful_downloads += 1
                total_size += download_result.file_size
        
        # Final statistics
        summary = progress_tracker.get_summary()
        print(f"\n📊 Download Summary:")
        print(f"   Total downloads: {summary['total']}")
        print(f"   Successful: {summary['completed']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Success rate: {summary['success_rate']:.1f}%")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Total size: {total_size / (1024*1024):.2f} MB")
        print(f"   Average speed: {total_size / total_time / (1024*1024):.2f} MB/s")
        
    except Exception as e:
        print(f"❌ Concurrent download example failed: {e}")


async def error_recovery_example():
    """Example: Advanced error handling and recovery strategies"""
    print("\n" + "=" * 60)
    print("ERROR RECOVERY EXAMPLE")
    print("=" * 60)
    
    # Initialize handler with error monitoring
    config = {
        'enable_caching': True,
        'enable_concurrent_processing': False,  # Easier for error demonstration
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 30,
            'circuit_breaker': {
                'enabled': True,
                'failure_threshold': 5,
                'recovery_timeout': 60
            }
        }
    }
    
    handler = TikTokHandler(config=config)
    
    # Test various error scenarios and recovery strategies
    error_scenarios = [
        {
            'name': 'Rate Limited URL',
            'url': 'https://www.tiktok.com/@rate_limited/video/1111111111111111111',
            'expected_error': 'rate_limit',
            'recovery_strategy': 'exponential_backoff'
        },
        {
            'name': 'Private Video',
            'url': 'https://www.tiktok.com/@private/video/2222222222222222222',
            'expected_error': 'access_denied',
            'recovery_strategy': 'quality_degradation'
        },
        {
            'name': 'Deleted Video',
            'url': 'https://www.tiktok.com/@deleted/video/3333333333333333333',
            'expected_error': 'not_found',
            'recovery_strategy': 'none'
        },
        {
            'name': 'Network Timeout',
            'url': 'https://www.tiktok.com/@timeout/video/4444444444444444444',
            'expected_error': 'network_timeout',
            'recovery_strategy': 'retry_with_fallback'
        }
    ]
    
    successful_recoveries = 0
    total_scenarios = len(error_scenarios)
    
    for i, scenario in enumerate(error_scenarios, 1):
        print(f"\n🧪 Scenario {i}: {scenario['name']}")
        print(f"🔗 URL: {scenario['url']}")
        print(f"🎯 Expected error: {scenario['expected_error']}")
        print(f"🔧 Recovery strategy: {scenario['recovery_strategy']}")
        
        try:
            # Attempt initial request
            print("📡 Making initial request...")
            video_info = await handler.get_video_info(scenario['url'])
            print(f"✅ Unexpected success: {video_info.title}")
            successful_recoveries += 1
            
        except Exception as initial_error:
            print(f"❌ Initial request failed: {type(initial_error).__name__}: {initial_error}")
            
            # Check if error has recovery context
            recovery_attempted = False
            
            if hasattr(initial_error, 'context') and initial_error.context:
                context = initial_error.context
                recovery_options = getattr(context, 'recovery_options', [])
                
                if recovery_options:
                    print(f"🔄 Available recovery options: {', '.join(recovery_options)}")
                    
                    # Simulate recovery attempt based on strategy
                    if scenario['recovery_strategy'] == 'exponential_backoff':
                        print("⏱️  Attempting recovery with exponential backoff...")
                        await asyncio.sleep(2)  # Simulate backoff
                        recovery_attempted = True
                        
                    elif scenario['recovery_strategy'] == 'quality_degradation':
                        print("📉 Attempting recovery with quality degradation...")
                        # Would implement quality fallback here
                        recovery_attempted = True
                        
                    elif scenario['recovery_strategy'] == 'retry_with_fallback':
                        print("🔄 Attempting recovery with fallback method...")
                        await asyncio.sleep(1)  # Simulate retry delay
                        recovery_attempted = True
            
            if recovery_attempted:
                try:
                    # Simulate recovery attempt (would be actual retry in real implementation)
                    print("🔄 Executing recovery strategy...")
                    # In real implementation, would retry with modified parameters
                    # For demo, we'll just simulate potential success
                    
                    if scenario['recovery_strategy'] != 'none':
                        print("✅ Recovery strategy completed (simulated)")
                        successful_recoveries += 1
                    else:
                        print("❌ No recovery strategy available")
                        
                except Exception as recovery_error:
                    print(f"❌ Recovery attempt failed: {recovery_error}")
            else:
                print("⚠️  No recovery context available")
        
        # Small delay between scenarios
        await asyncio.sleep(1)
    
    # Recovery statistics
    recovery_rate = (successful_recoveries / total_scenarios) * 100
    print(f"\n📊 Error Recovery Summary:")
    print(f"   Total scenarios: {total_scenarios}")
    print(f"   Successful recoveries: {successful_recoveries}")
    print(f"   Recovery rate: {recovery_rate:.1f}%")


async def performance_monitoring_example():
    """Example: Performance monitoring and optimization"""
    print("\n" + "=" * 60)
    print("PERFORMANCE MONITORING EXAMPLE")
    print("=" * 60)
    
    # Initialize enhanced handler with monitoring
    enhanced_handler = EnhancedTikTokHandler({
        'enable_caching': True,
        'enable_concurrent_processing': True,
        'max_concurrent_operations': 5
    })
    
    print("📊 Performance monitoring enabled")
    
    # Test URLs for performance measurement
    test_urls = [
        "https://www.tiktok.com/@perf1/video/1111111111111111111",
        "https://www.tiktok.com/@perf2/video/2222222222222222222",
        "https://www.tiktok.com/@perf3/video/3333333333333333333"
    ]
    
    # Warm up cache
    print("🔥 Warming up cache...")
    for url in test_urls[:1]:  # Warm up with first URL
        try:
            await enhanced_handler.get_video_info(url)
        except:
            pass  # Ignore errors during warmup
    
    # Performance test runs
    test_runs = 3
    run_times = []
    
    for run in range(test_runs):
        print(f"\n🏃 Performance run {run + 1}/{test_runs}")
        
        start_time = time.time()
        
        try:
            # Concurrent requests
            tasks = [enhanced_handler.get_video_info(url) for url in test_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            run_time = time.time() - start_time
            run_times.append(run_time)
            
            successful = sum(1 for r in results if not isinstance(r, Exception))
            print(f"   ⏱️  Run time: {run_time:.2f}s")
            print(f"   ✅ Successful: {successful}/{len(test_urls)}")
            
        except Exception as e:
            print(f"   ❌ Run failed: {e}")
    
    # Performance statistics
    if run_times:
        avg_time = sum(run_times) / len(run_times)
        min_time = min(run_times)
        max_time = max(run_times)
        
        print(f"\n📈 Performance Statistics:")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Best time: {min_time:.2f}s")
        print(f"   Worst time: {max_time:.2f}s")
        print(f"   Performance consistency: {((max_time - min_time) / avg_time * 100):.1f}% variance")
    
    # Cache effectiveness
    cache_stats = enhanced_handler.get_cache_statistics()
    if cache_stats:
        print(f"\n💾 Cache Effectiveness:")
        print(f"   Cache entries: {cache_stats.get('cache_size', 0)}")
        print(f"   Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
        print(f"   Memory usage: {cache_stats.get('memory_usage', 0):.2f} MB")
    
    # Resource usage
    performance_stats = enhanced_handler.get_performance_statistics()
    if performance_stats:
        print(f"\n⚡ Resource Usage:")
        print(f"   Total requests: {performance_stats.get('total_requests', 0)}")
        print(f"   Average response time: {performance_stats.get('avg_response_time', 0):.2f}s")
        print(f"   Errors: {performance_stats.get('error_count', 0)}")
        print(f"   Concurrent operations: {performance_stats.get('concurrent_operations', 0)}")


async def custom_configuration_example():
    """Example: Custom configuration for specific use cases"""
    print("\n" + "=" * 60)
    print("CUSTOM CONFIGURATION EXAMPLE")
    print("=" * 60)
    
    # High-throughput configuration
    high_throughput_config = {
        'enable_caching': True,
        'cache_ttl': 7200,  # 2 hours
        'cache_max_size': 10000,
        'enable_concurrent_processing': True,
        'max_concurrent_operations': 20,
        'connection_pool_size': 50,
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 240,
            'adaptive_limiting': True,
            'burst_limit': 20
        }
    }
    
    # Memory-optimized configuration  
    memory_optimized_config = {
        'enable_caching': True,
        'cache_ttl': 900,  # 15 minutes
        'cache_max_size': 500,
        'enable_concurrent_processing': False,
        'memory_optimization': True,
        'lazy_loading': True,
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 60
        }
    }
    
    # Network-conservative configuration
    conservative_config = {
        'enable_caching': True,
        'cache_ttl': 3600,
        'enable_concurrent_processing': False,
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 20,
            'min_request_interval': 3.0,
            'exponential_backoff': True
        },
        'connection_timeout': 60,
        'retry_attempts': 5
    }
    
    configurations = [
        ("High Throughput", high_throughput_config),
        ("Memory Optimized", memory_optimized_config),
        ("Network Conservative", conservative_config)
    ]
    
    test_url = "https://www.tiktok.com/@config/video/1111111111111111111"
    
    for config_name, config in configurations:
        print(f"\n🔧 Testing {config_name} Configuration")
        print(f"   Cache TTL: {config.get('cache_ttl', 'default')}")
        print(f"   Concurrent: {config.get('enable_concurrent_processing', False)}")
        print(f"   Rate limit: {config.get('rate_limit', {}).get('requests_per_minute', 'default')}")
        
        try:
            handler = TikTokHandler(config=config)
            
            start_time = time.time()
            video_info = await handler.get_video_info(test_url)
            response_time = time.time() - start_time
            
            print(f"   ⏱️  Response time: {response_time:.2f}s")
            print(f"   ✅ Configuration working: {video_info.title[:30]}...")
            
        except Exception as e:
            print(f"   ❌ Configuration failed: {e}")


async def main():
    """Run all advanced examples"""
    print("🚀 TikTok Handler Advanced Usage Examples")
    print("==========================================")
    
    try:
        # Run advanced examples
        await enhanced_handler_example()
        await concurrent_download_example()
        await error_recovery_example()
        await performance_monitoring_example()
        await custom_configuration_example()
        
        print("\n" + "=" * 60)
        print("✅ ALL ADVANCED EXAMPLES COMPLETED!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n🛑 Advanced examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Advanced examples failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("⚠️  Note: Replace test URLs with actual TikTok URLs for real testing")
    print("🔗 Test URLs in this example are placeholders")
    print("🧪 Advanced examples include simulated scenarios for demonstration")
    
    # Run the advanced examples
    asyncio.run(main()) 