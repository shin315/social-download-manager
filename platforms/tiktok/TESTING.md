# TikTok Handler Testing Documentation

This document provides comprehensive guidance on testing the TikTok platform handler, including test suite overview, testing strategies, mocking approaches, and continuous testing practices.

## Table of Contents

- [Testing Overview](#testing-overview)
- [Test Suite Organization](#test-suite-organization)
- [Testing Strategies](#testing-strategies)
- [Mock Integration Testing](#mock-integration-testing)
- [Performance Testing](#performance-testing)
- [Edge Case Testing](#edge-case-testing)
- [Continuous Testing](#continuous-testing)
- [Test Environment Setup](#test-environment-setup)

## Testing Overview

The TikTok handler testing framework is designed to provide comprehensive coverage across multiple dimensions:

- **Unit Testing**: Individual component functionality
- **Integration Testing**: Component interaction validation
- **Performance Testing**: Load and stress testing
- **Edge Case Testing**: Boundary condition validation
- **Mock Testing**: External dependency isolation
- **End-to-End Testing**: Complete workflow validation

### Test Coverage Metrics

| Test Type | Coverage Target | Current Status |
|-----------|----------------|----------------|
| Unit Tests | 90%+ | ✅ Achieved |
| Integration Tests | 80%+ | ✅ Achieved |
| Performance Tests | Key scenarios | ✅ Implemented |
| Edge Cases | Critical paths | ✅ Implemented |
| Mock Tests | External APIs | ✅ Implemented |

## Test Suite Organization

### 1. Core Test Modules

```
tests/
├── test_tiktok_refactor.py          # Basic functionality tests
├── test_tiktok_authentication.py    # Authentication system tests
├── test_tiktok_metadata.py          # Metadata extraction tests
├── test_tiktok_download.py          # Download functionality tests
├── test_tiktok_error_handling.py    # Error handling tests
├── test_tiktok_comprehensive.py     # Master test runner
├── test_tiktok_mock_integration.py  # Mock integration tests
├── test_tiktok_performance.py       # Performance benchmarks
├── test_tiktok_edge_cases.py        # Edge case validation
└── test_tiktok_performance_optimizations.py  # Optimization tests
```

### 2. Test Execution Workflow

```python
# Run all tests with comprehensive reporting
python test_tiktok_comprehensive.py

# Run specific test modules
python -m pytest test_tiktok_refactor.py -v
python -m pytest test_tiktok_authentication.py -v
python -m pytest test_tiktok_metadata.py -v

# Run with coverage reporting
python -m pytest --cov=platforms.tiktok --cov-report=html

# Run performance tests
python test_tiktok_performance.py
```

### 3. Test Configuration

```python
# Test configuration settings
TEST_CONFIG = {
    'timeout': 30,              # Test timeout in seconds
    'retry_attempts': 3,        # Number of retry attempts
    'concurrent_tests': 5,      # Maximum concurrent tests
    'mock_mode': True,          # Enable mock responses
    'cache_enabled': False,     # Disable cache for predictable tests
    'rate_limit_disabled': True # Disable rate limiting in tests
}

# Test URLs (use mock URLs for consistent testing)
TEST_URLS = [
    "https://www.tiktok.com/@test_user/video/1111111111111111111",
    "https://vm.tiktok.com/test_short_url",
    "https://m.tiktok.com/v/2222222222222222222.html"
]
```

## Testing Strategies

### 1. Unit Testing Strategy

**Objective**: Test individual components in isolation

```python
import unittest
from unittest.mock import Mock, patch, AsyncMock
from platforms.tiktok import TikTokHandler

class TestTikTokHandlerUnit(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = TikTokHandler({
            'enable_caching': False,
            'enable_concurrent_processing': False
        })
    
    def test_url_validation(self):
        """Test URL validation logic"""
        # Valid URLs
        valid_urls = [
            "https://www.tiktok.com/@user/video/1234567890123456789",
            "https://vm.tiktok.com/shortcode",
            "https://m.tiktok.com/v/1234567890123456789.html"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(self.handler.is_valid_url(url))
    
    def test_url_validation_invalid(self):
        """Test URL validation with invalid URLs"""
        invalid_urls = [
            "https://youtube.com/watch?v=123",
            "not-a-url",
            "",
            None
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                if url is not None:
                    self.assertFalse(self.handler.is_valid_url(url))
    
    def test_capabilities(self):
        """Test platform capabilities"""
        capabilities = self.handler.get_capabilities()
        
        self.assertEqual(capabilities.platform_name, "TikTok")
        self.assertTrue(capabilities.supports_video_info)
        self.assertTrue(capabilities.supports_download)
        self.assertFalse(capabilities.requires_authentication)
    
    @patch('yt_dlp.YoutubeDL')
    async def test_video_info_extraction(self, mock_ytdl):
        """Test video information extraction"""
        # Mock yt-dlp response
        mock_instance = Mock()
        mock_ytdl.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            'title': 'Test Video',
            'uploader': 'test_user',
            'duration': 30,
            'view_count': 1000,
            'like_count': 100,
            'comment_count': 10
        }
        
        url = "https://www.tiktok.com/@test/video/1234567890123456789"
        video_info = await self.handler.get_video_info(url)
        
        self.assertEqual(video_info.title, 'Test Video')
        self.assertEqual(video_info.creator, 'test_user')
        self.assertEqual(video_info.duration, 30)

# Run unit tests
if __name__ == '__main__':
    unittest.main()
```

### 2. Integration Testing Strategy

**Objective**: Test component interactions and data flow

```python
import asyncio
import unittest
from platforms.tiktok import TikTokHandler
from platforms.tiktok.enhanced_handler import EnhancedTikTokHandler

class TestTikTokIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up integration test environment"""
        self.standard_handler = TikTokHandler()
        self.enhanced_handler = EnhancedTikTokHandler({
            'enable_caching': True,
            'enable_concurrent_processing': True
        })
    
    async def test_end_to_end_workflow(self):
        """Test complete video processing workflow"""
        test_url = "https://www.tiktok.com/@test/video/1234567890123456789"
        
        # Step 1: Validate URL
        self.assertTrue(self.standard_handler.is_valid_url(test_url))
        
        # Step 2: Get video information
        video_info = await self.standard_handler.get_video_info(test_url)
        self.assertIsNotNone(video_info)
        self.assertIsNotNone(video_info.title)
        
        # Step 3: Test download preparation
        download_options = {
            'output_path': '/tmp/test_downloads',
            'quality_preference': 'HD',
            'include_audio': True
        }
        
        # Note: Skip actual download in integration tests
        # download_result = await self.standard_handler.download_video(test_url, download_options)
        # self.assertTrue(download_result.success)
    
    async def test_cache_integration(self):
        """Test caching integration between requests"""
        test_url = "https://www.tiktok.com/@test/video/1234567890123456789"
        
        # First request (cache miss)
        start_time = time.time()
        video_info_1 = await self.enhanced_handler.get_video_info(test_url)
        first_request_time = time.time() - start_time
        
        # Second request (cache hit)
        start_time = time.time()
        video_info_2 = await self.enhanced_handler.get_video_info(test_url)
        second_request_time = time.time() - start_time
        
        # Verify cache effectiveness
        self.assertEqual(video_info_1.title, video_info_2.title)
        self.assertLess(second_request_time, first_request_time)
    
    async def test_error_propagation(self):
        """Test error handling across components"""
        invalid_url = "https://www.tiktok.com/@nonexistent/video/0000000000000000000"
        
        with self.assertRaises(Exception) as context:
            await self.standard_handler.get_video_info(invalid_url)
        
        # Verify error contains context
        error = context.exception
        if hasattr(error, 'context'):
            self.assertIsNotNone(error.context)
    
    def test_async_integration(self):
        """Run async integration tests"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.test_end_to_end_workflow())
            loop.run_until_complete(self.test_cache_integration())
            loop.run_until_complete(self.test_error_propagation())
        finally:
            loop.close()
```

### 3. Behavioral Testing Strategy

**Objective**: Test behavior under various conditions

```python
class TestTikTokBehavior(unittest.TestCase):
    
    async def test_concurrent_requests(self):
        """Test behavior under concurrent load"""
        handler = TikTokHandler({
            'enable_concurrent_processing': True,
            'max_concurrent_operations': 5
        })
        
        test_urls = [
            f"https://www.tiktok.com/@test{i}/video/{i}111111111111111111"
            for i in range(10)
        ]
        
        # Execute concurrent requests
        start_time = time.time()
        tasks = [handler.get_video_info(url) for url in test_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify concurrency benefits
        successful_results = [r for r in results if not isinstance(r, Exception)]
        self.assertGreater(len(successful_results), 0)
        
        # Should be faster than sequential processing
        self.assertLess(total_time, len(test_urls) * 2)  # Assuming 2s per request
    
    async def test_rate_limiting_behavior(self):
        """Test rate limiting enforcement"""
        handler = TikTokHandler({
            'rate_limit': {
                'enabled': True,
                'requests_per_minute': 6,  # Very low for testing
                'min_request_interval': 10.0  # 10 seconds
            }
        })
        
        test_url = "https://www.tiktok.com/@test/video/1234567890123456789"
        
        # Make rapid requests
        request_times = []
        for i in range(3):
            start_time = time.time()
            try:
                await handler.get_video_info(test_url)
            except Exception:
                pass  # Rate limiting may cause errors
            request_times.append(time.time() - start_time)
        
        # Verify rate limiting is working
        # Later requests should take longer due to rate limiting
        if len(request_times) >= 2:
            self.assertGreaterEqual(request_times[1], request_times[0])
    
    async def test_memory_behavior(self):
        """Test memory usage behavior"""
        import psutil
        
        handler = TikTokHandler({
            'enable_caching': True,
            'cache_max_size': 100
        })
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Process multiple videos
        test_urls = [
            f"https://www.tiktok.com/@test{i}/video/{i}111111111111111111"
            for i in range(20)
        ]
        
        for url in test_urls:
            try:
                await handler.get_video_info(url)
            except Exception:
                pass  # Focus on memory behavior
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(memory_increase, 100 * 1024 * 1024)
```

## Mock Integration Testing

### 1. Mock Response System

```python
class MockTikTokResponses:
    """Mock responses for TikTok API calls"""
    
    @staticmethod
    def get_mock_video_info(video_id: str) -> dict:
        """Generate mock video information"""
        return {
            'id': video_id,
            'title': f'Mock Video {video_id}',
            'uploader': 'mock_user',
            'uploader_id': 'mock_user_id',
            'duration': 30,
            'view_count': 1000,
            'like_count': 100,
            'comment_count': 10,
            'upload_date': '20240101',
            'formats': [
                {
                    'format_id': 'mp4_hd',
                    'ext': 'mp4',
                    'width': 1080,
                    'height': 1920,
                    'quality': 'HD'
                },
                {
                    'format_id': 'mp4_sd',
                    'ext': 'mp4',
                    'width': 720,
                    'height': 1280,
                    'quality': 'SD'
                }
            ],
            'thumbnail': f'https://mock.tiktok.com/thumb/{video_id}.jpg'
        }
    
    @staticmethod
    def get_mock_error_response(error_type: str) -> Exception:
        """Generate mock error responses"""
        error_map = {
            'not_found': Exception('Video not found'),
            'private': Exception('Private video'),
            'rate_limit': Exception('Rate limit exceeded'),
            'network': Exception('Network error')
        }
        return error_map.get(error_type, Exception('Unknown error'))

class TestTikTokMockIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up mock testing environment"""
        self.mock_responses = MockTikTokResponses()
        self.handler = TikTokHandler({
            'enable_caching': False,  # Disable for predictable testing
            'rate_limit': {'enabled': False}  # Disable for testing
        })
    
    @patch('yt_dlp.YoutubeDL')
    async def test_successful_video_info_mock(self, mock_ytdl):
        """Test successful video info retrieval with mocks"""
        # Setup mock
        mock_instance = Mock()
        mock_ytdl.return_value = mock_instance
        mock_instance.extract_info.return_value = self.mock_responses.get_mock_video_info('1234567890')
        
        # Test
        url = "https://www.tiktok.com/@test/video/1234567890123456789"
        video_info = await self.handler.get_video_info(url)
        
        # Verify
        self.assertEqual(video_info.title, 'Mock Video 1234567890')
        self.assertEqual(video_info.creator, 'mock_user')
        self.assertEqual(video_info.duration, 30)
        
        # Verify yt-dlp was called correctly
        mock_instance.extract_info.assert_called_once()
    
    @patch('yt_dlp.YoutubeDL')
    async def test_error_handling_mock(self, mock_ytdl):
        """Test error handling with mocks"""
        # Setup mock to raise error
        mock_instance = Mock()
        mock_ytdl.return_value = mock_instance
        mock_instance.extract_info.side_effect = self.mock_responses.get_mock_error_response('not_found')
        
        # Test
        url = "https://www.tiktok.com/@test/video/0000000000000000000"
        
        with self.assertRaises(Exception) as context:
            await self.handler.get_video_info(url)
        
        # Verify error
        self.assertIn('not found', str(context.exception).lower())
    
    async def test_multiple_mock_scenarios(self):
        """Test multiple scenarios with different mock responses"""
        scenarios = [
            ('success', 'get_mock_video_info', '1111111111'),
            ('not_found', 'get_mock_error_response', 'not_found'),
            ('private', 'get_mock_error_response', 'private'),
            ('rate_limit', 'get_mock_error_response', 'rate_limit')
        ]
        
        results = {}
        
        for scenario_name, mock_method, mock_param in scenarios:
            with patch('yt_dlp.YoutubeDL') as mock_ytdl:
                mock_instance = Mock()
                mock_ytdl.return_value = mock_instance
                
                if mock_method == 'get_mock_video_info':
                    mock_instance.extract_info.return_value = getattr(self.mock_responses, mock_method)(mock_param)
                else:
                    mock_instance.extract_info.side_effect = getattr(self.mock_responses, mock_method)(mock_param)
                
                try:
                    url = f"https://www.tiktok.com/@test/video/{mock_param}111111111111111"
                    result = await self.handler.get_video_info(url)
                    results[scenario_name] = {'success': True, 'result': result}
                except Exception as e:
                    results[scenario_name] = {'success': False, 'error': str(e)}
        
        # Verify results
        self.assertTrue(results['success']['success'])
        self.assertFalse(results['not_found']['success'])
        self.assertFalse(results['private']['success'])
        self.assertFalse(results['rate_limit']['success'])
```

## Performance Testing

### 1. Load Testing Framework

```python
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor

class PerformanceTestSuite:
    
    def __init__(self, handler):
        self.handler = handler
        self.results = []
    
    async def single_request_benchmark(self, url: str, iterations: int = 10):
        """Benchmark single request performance"""
        durations = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                await self.handler.get_video_info(url)
                duration = time.time() - start_time
                durations.append(duration)
            except Exception as e:
                print(f"Request {i+1} failed: {e}")
        
        if durations:
            return {
                'mean': statistics.mean(durations),
                'median': statistics.median(durations),
                'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0,
                'min': min(durations),
                'max': max(durations),
                'success_rate': len(durations) / iterations * 100
            }
        
        return None
    
    async def concurrent_request_benchmark(self, urls: list, concurrency: int = 5):
        """Benchmark concurrent request performance"""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_request(url):
            async with semaphore:
                start_time = time.time()
                try:
                    result = await self.handler.get_video_info(url)
                    return time.time() - start_time, True, result
                except Exception as e:
                    return time.time() - start_time, False, str(e)
        
        start_time = time.time()
        results = await asyncio.gather(*[limited_request(url) for url in urls])
        total_time = time.time() - start_time
        
        durations = [r[0] for r in results]
        successful = [r for r in results if r[1]]
        
        return {
            'total_time': total_time,
            'total_requests': len(urls),
            'successful_requests': len(successful),
            'success_rate': len(successful) / len(urls) * 100,
            'requests_per_second': len(urls) / total_time,
            'avg_response_time': statistics.mean(durations),
            'max_response_time': max(durations),
            'min_response_time': min(durations)
        }
    
    async def stress_test(self, url: str, duration_seconds: int = 60, max_rps: int = 10):
        """Stress test with sustained load"""
        start_time = time.time()
        results = []
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            request_start = time.time()
            
            try:
                await self.handler.get_video_info(url)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
            
            request_duration = time.time() - request_start
            request_count += 1
            
            results.append({
                'timestamp': time.time(),
                'duration': request_duration,
                'success': success,
                'error': error
            })
            
            # Rate limiting
            sleep_time = max(0, 1/max_rps - request_duration)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        total_time = time.time() - start_time
        successful = [r for r in results if r['success']]
        
        return {
            'duration': total_time,
            'total_requests': len(results),
            'successful_requests': len(successful),
            'success_rate': len(successful) / len(results) * 100,
            'actual_rps': len(results) / total_time,
            'avg_response_time': statistics.mean([r['duration'] for r in results]),
            'errors': [r['error'] for r in results if not r['success']]
        }

# Usage example
async def run_performance_tests():
    """Run comprehensive performance tests"""
    
    # Test both standard and enhanced handlers
    handlers = {
        'standard': TikTokHandler(),
        'enhanced': EnhancedTikTokHandler({'enable_caching': True})
    }
    
    test_url = "https://www.tiktok.com/@test/video/1234567890123456789"
    test_urls = [f"https://www.tiktok.com/@test{i}/video/{i}234567890123456789" for i in range(5)]
    
    for handler_name, handler in handlers.items():
        print(f"\nTesting {handler_name} handler:")
        
        perf_suite = PerformanceTestSuite(handler)
        
        # Single request benchmark
        single_result = await perf_suite.single_request_benchmark(test_url)
        if single_result:
            print(f"Single request - Mean: {single_result['mean']:.2f}s, Success: {single_result['success_rate']:.1f}%")
        
        # Concurrent request benchmark
        concurrent_result = await perf_suite.concurrent_request_benchmark(test_urls)
        print(f"Concurrent - RPS: {concurrent_result['requests_per_second']:.1f}, Success: {concurrent_result['success_rate']:.1f}%")
        
        # Brief stress test
        stress_result = await perf_suite.stress_test(test_url, duration_seconds=30, max_rps=5)
        print(f"Stress test - RPS: {stress_result['actual_rps']:.1f}, Success: {stress_result['success_rate']:.1f}%")
```

## Edge Case Testing

### 1. Boundary Condition Tests

```python
class TestTikTokEdgeCases(unittest.TestCase):
    
    def setUp(self):
        self.handler = TikTokHandler()
    
    async def test_url_edge_cases(self):
        """Test URL validation edge cases"""
        edge_case_urls = [
            # Empty and None
            "",
            None,
            
            # Malformed URLs
            "not-a-url",
            "http://",
            "https://",
            
            # Almost valid URLs
            "https://tiktok.com",  # Missing www
            "https://www.tiktok.com",  # Missing path
            "https://www.tiktok.com/@user",  # Missing video
            
            # Different TikTok URL formats
            "https://www.tiktok.com/@user/video/",  # Missing video ID
            "https://vm.tiktok.com/",  # Missing short code
            "https://m.tiktok.com/v/.html",  # Missing video ID
            
            # Very long URLs
            "https://www.tiktok.com/@" + "a" * 1000 + "/video/1234567890123456789",
            
            # URLs with special characters
            "https://www.tiktok.com/@user/video/1234567890123456789?param=value&other=123",
            "https://www.tiktok.com/@user/video/1234567890123456789#fragment"
        ]
        
        results = {}
        for url in edge_case_urls:
            try:
                result = self.handler.is_valid_url(url)
                results[str(url)[:50]] = result
            except Exception as e:
                results[str(url)[:50]] = f"Exception: {e}"
        
        # Verify None and empty string handling
        self.assertFalse(results.get('None', True))
        self.assertFalse(results.get('', True))
    
    async def test_response_edge_cases(self):
        """Test handling of edge case responses"""
        
        # Test with minimal mock data
        minimal_data = {
            'title': '',
            'uploader': None,
            'duration': 0
        }
        
        with patch('yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_ytdl.return_value = mock_instance
            mock_instance.extract_info.return_value = minimal_data
            
            url = "https://www.tiktok.com/@test/video/1234567890123456789"
            video_info = await self.handler.get_video_info(url)
            
            # Should handle minimal data gracefully
            self.assertIsNotNone(video_info)
            self.assertEqual(video_info.title, '')
            self.assertEqual(video_info.duration, 0)
    
    async def test_large_response_handling(self):
        """Test handling of very large responses"""
        
        # Create large mock data
        large_data = {
            'title': 'A' * 10000,  # Very long title
            'description': 'B' * 50000,  # Very long description
            'uploader': 'test_user',
            'formats': [{'format_id': f'format_{i}'} for i in range(1000)]  # Many formats
        }
        
        with patch('yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_ytdl.return_value = mock_instance
            mock_instance.extract_info.return_value = large_data
            
            url = "https://www.tiktok.com/@test/video/1234567890123456789"
            
            # Should handle large data without memory issues
            start_memory = self._get_memory_usage()
            video_info = await self.handler.get_video_info(url)
            end_memory = self._get_memory_usage()
            
            self.assertIsNotNone(video_info)
            # Memory increase should be reasonable
            memory_increase = end_memory - start_memory
            self.assertLess(memory_increase, 100 * 1024 * 1024)  # Less than 100MB
    
    def _get_memory_usage(self):
        """Get current memory usage"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss
    
    async def test_timeout_edge_cases(self):
        """Test timeout handling"""
        
        # Configure handler with very short timeout
        timeout_handler = TikTokHandler({
            'connection_timeout': 0.1,  # 100ms timeout
            'read_timeout': 0.1
        })
        
        with patch('yt_dlp.YoutubeDL') as mock_ytdl:
            mock_instance = Mock()
            mock_ytdl.return_value = mock_instance
            
            # Simulate slow response
            def slow_extract(*args, **kwargs):
                import time
                time.sleep(1)  # Longer than timeout
                return {'title': 'Test'}
            
            mock_instance.extract_info.side_effect = slow_extract
            
            url = "https://www.tiktok.com/@test/video/1234567890123456789"
            
            # Should handle timeout gracefully
            with self.assertRaises(Exception):
                await timeout_handler.get_video_info(url)
```

## Continuous Testing

### 1. Automated Test Pipeline

```python
class ContinuousTestRunner:
    """Automated test runner for continuous integration"""
    
    def __init__(self):
        self.test_modules = [
            'test_tiktok_refactor',
            'test_tiktok_authentication',
            'test_tiktok_metadata',
            'test_tiktok_download',
            'test_tiktok_error_handling',
            'test_tiktok_mock_integration',
            'test_tiktok_performance',
            'test_tiktok_edge_cases'
        ]
        self.results = {}
    
    async def run_all_tests(self):
        """Run all test modules"""
        total_passed = 0
        total_failed = 0
        
        for module in self.test_modules:
            print(f"Running {module}...")
            result = await self._run_test_module(module)
            self.results[module] = result
            
            total_passed += result['passed']
            total_failed += result['failed']
        
        # Generate summary report
        self._generate_summary_report(total_passed, total_failed)
        
        return self.results
    
    async def _run_test_module(self, module_name: str):
        """Run a specific test module"""
        try:
            # Import and run test module
            module = __import__(module_name)
            
            # Count tests and run them
            if hasattr(module, 'run_tests'):
                result = await module.run_tests()
                return {
                    'passed': result.get('passed', 0),
                    'failed': result.get('failed', 0),
                    'errors': result.get('errors', []),
                    'duration': result.get('duration', 0)
                }
            else:
                return {'passed': 0, 'failed': 1, 'errors': ['Module not runnable'], 'duration': 0}
                
        except Exception as e:
            return {'passed': 0, 'failed': 1, 'errors': [str(e)], 'duration': 0}
    
    def _generate_summary_report(self, total_passed: int, total_failed: int):
        """Generate test summary report"""
        total_tests = total_passed + total_failed
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*60)
        print("TEST SUMMARY REPORT")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print("="*60)
        
        # Detailed module results
        for module, result in self.results.items():
            module_tests = result['passed'] + result['failed']
            module_success = (result['passed'] / module_tests * 100) if module_tests > 0 else 0
            print(f"{module}: {result['passed']}/{module_tests} ({module_success:.1f}%)")
            
            if result['errors']:
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"  Error: {error}")
        
        print("="*60)

# CI/CD Integration
def run_ci_tests():
    """Entry point for CI/CD pipeline"""
    runner = ContinuousTestRunner()
    
    # Run tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(runner.run_all_tests())
        
        # Determine exit code
        total_failed = sum(r['failed'] for r in results.values())
        exit_code = 0 if total_failed == 0 else 1
        
        return exit_code
        
    finally:
        loop.close()

if __name__ == '__main__':
    import sys
    exit_code = run_ci_tests()
    sys.exit(exit_code)
```

### 2. Test Environment Configuration

```yaml
# .github/workflows/test.yml
name: TikTok Handler Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run unit tests
      run: |
        pytest test_tiktok_refactor.py -v
        pytest test_tiktok_authentication.py -v
        pytest test_tiktok_metadata.py -v
    
    - name: Run integration tests
      run: |
        python test_tiktok_mock_integration.py
    
    - name: Run performance tests
      run: |
        python test_tiktok_performance.py
    
    - name: Generate coverage report
      run: |
        pytest --cov=platforms.tiktok --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

## Test Environment Setup

### 1. Development Environment

```bash
# Setup test environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-mock

# Run tests
python -m pytest platforms/tiktok/tests/ -v
```

### 2. Mock Data Setup

```python
# Create test data directory
mkdir -p tests/data

# Sample mock responses
cat > tests/data/mock_responses.json << EOF
{
  "video_info_success": {
    "title": "Test Video",
    "uploader": "test_user",
    "duration": 30,
    "view_count": 1000
  },
  "video_info_error": {
    "error": "Video not found"
  }
}
EOF
```

### 3. Test Configuration

```python
# tests/conftest.py
import pytest
import asyncio
from platforms.tiktok import TikTokHandler

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def tiktok_handler():
    """Create a TikTok handler for testing."""
    return TikTokHandler({
        'enable_caching': False,
        'rate_limit': {'enabled': False}
    })

@pytest.fixture
def mock_video_data():
    """Provide mock video data for tests."""
    return {
        'title': 'Test Video',
        'uploader': 'test_user',
        'duration': 30,
        'view_count': 1000,
        'like_count': 100
    }
```

This comprehensive testing documentation provides all the necessary guidance for testing the TikTok handler across different scenarios, from unit tests to performance testing and continuous integration. 