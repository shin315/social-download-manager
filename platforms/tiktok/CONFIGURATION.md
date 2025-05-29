# TikTok Handler Configuration Guide

This document provides comprehensive configuration options for the TikTok platform handler, including authentication, performance optimization, caching, session management, and rate limiting settings.

## Table of Contents

- [Basic Configuration](#basic-configuration)
- [Authentication Configuration](#authentication-configuration)
- [Performance Configuration](#performance-configuration)
- [Cache Configuration](#cache-configuration)
- [Session Management](#session-management)
- [Rate Limiting Configuration](#rate-limiting-configuration)
- [Environment Variables](#environment-variables)
- [Advanced Configuration](#advanced-configuration)

## Basic Configuration

### Default Configuration

```python
from platforms.tiktok import TikTokHandler

# Basic handler with default settings
handler = TikTokHandler()

# Basic handler with minimal config
handler = TikTokHandler(config={
    'enable_caching': True,
    'enable_concurrent_processing': True
})
```

### Configuration Structure

```python
config = {
    # Core settings
    'enable_caching': True,
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 5,
    
    # Authentication (optional for public content)
    'enable_authentication': False,
    'session_config': {...},
    'headers_config': {...},
    'proxy_config': {...},
    
    # Performance optimization
    'cache_ttl': 1800,  # 30 minutes
    'cache_max_size': 1000,
    'connection_pool_size': 10,
    
    # Rate limiting
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 60,
        'min_request_interval': 1.0
    }
}

handler = TikTokHandler(config=config)
```

## Authentication Configuration

### Public Content Access (Default)

For public TikTok videos, no authentication is required:

```python
auth_config = {
    'enable_authentication': False,  # Default for public content
    'requires_api_key': False,
    'session_management': True  # Still useful for rate limiting
}
```

### Session Management

Configure session handling for optimal performance:

```python
session_config = {
    'cookies_file': 'tiktok_cookies.txt',  # Optional cookie persistence
    'session_timeout': 3600,  # 1 hour
    'auto_refresh': True,
    'track_requests': True,
    'max_requests_per_session': 1000
}

config = {
    'session_config': session_config
}
```

### Headers Configuration

Customize HTTP headers and user agent rotation:

```python
headers_config = {
    'user_agent_rotation': True,
    'rotation_interval': 100,  # Rotate every 100 requests
    'custom_headers': {
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1'
    },
    'random_user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...',
        # Add more user agents as needed
    ]
}

config = {
    'headers_config': headers_config
}
```

### Proxy Configuration

Configure proxy settings for geo-restrictions or privacy:

```python
proxy_config = {
    'enabled': False,  # Disable by default
    'proxy_url': 'http://proxy.example.com:8080',
    'proxy_auth': {
        'username': 'proxy_user',
        'password': 'proxy_pass'
    },
    'rotation_enabled': False,
    'proxy_list': [
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080'
    ],
    'fallback_to_direct': True  # Use direct connection if proxy fails
}

config = {
    'proxy_config': proxy_config
}
```

### Future API Authentication

For future official TikTok API integration:

```python
api_auth_config = {
    'enable_authentication': True,
    'auth_type': 'bearer_token',  # or 'oauth', 'api_key'
    'credentials': {
        'api_key': 'your_api_key',
        'api_secret': 'your_api_secret',
        'access_token': 'your_access_token',
        'refresh_token': 'your_refresh_token'
    },
    'token_refresh': {
        'auto_refresh': True,
        'refresh_threshold': 300,  # Refresh 5 minutes before expiry
        'refresh_endpoint': 'https://api.tiktok.com/auth/refresh'
    }
}

# Note: This is for future use when official API is integrated
```

## Performance Configuration

### Cache Configuration

Configure caching for optimal performance:

```python
cache_config = {
    'enable_caching': True,
    'cache_ttl': 1800,  # 30 minutes default
    'cache_max_size': 1000,  # Maximum cache entries
    'cache_types': {
        'video_info': {
            'enabled': True,
            'ttl': 1800  # 30 minutes
        },
        'format_selection': {
            'enabled': True,
            'ttl': 3600  # 1 hour
        },
        'metadata_extraction': {
            'enabled': True,
            'ttl': 1800  # 30 minutes
        },
        'upload_date_parsing': {
            'enabled': True,
            'ttl': 86400  # 24 hours
        }
    },
    'cache_cleanup': {
        'interval': 300,  # 5 minutes
        'auto_cleanup': True
    }
}

config = {
    'cache_config': cache_config
}
```

### Connection Pooling

Optimize HTTP connections:

```python
connection_config = {
    'connection_pool_size': 10,
    'max_connections_per_host': 5,
    'connection_timeout': 30,  # seconds
    'read_timeout': 60,  # seconds
    'keep_alive': True,
    'keep_alive_timeout': 30,
    'retry_attempts': 3,
    'retry_backoff': 1.0  # seconds
}

config = {
    'connection_config': connection_config
}
```

### Concurrent Processing

Configure parallel processing:

```python
concurrency_config = {
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 5,
    'max_concurrent_downloads': 3,
    'max_concurrent_metadata_extractions': 10,
    'task_queue_size': 100,
    'worker_timeout': 300  # 5 minutes
}

config = {
    'concurrency_config': concurrency_config
}
```

### Memory Optimization

Configure memory usage:

```python
memory_config = {
    'lazy_loading': True,
    'batch_size': 100,
    'max_memory_usage': 512,  # MB
    'garbage_collection': {
        'enabled': True,
        'interval': 300,  # 5 minutes
        'threshold': 0.8  # Trigger at 80% memory usage
    }
}

config = {
    'memory_config': memory_config
}
```

## Rate Limiting Configuration

### Basic Rate Limiting

```python
rate_limit_config = {
    'enabled': True,
    'requests_per_minute': 60,
    'requests_per_hour': 1000,
    'burst_limit': 10,  # Allow bursts up to 10 requests
    'min_request_interval': 1.0,  # Minimum 1 second between requests
    'adaptive_limiting': True  # Adjust based on response times
}

config = {
    'rate_limit': rate_limit_config
}
```

### Advanced Rate Limiting

```python
advanced_rate_limit = {
    'enabled': True,
    'strategies': {
        'token_bucket': {
            'capacity': 100,
            'refill_rate': 10,  # tokens per minute
            'refill_interval': 6  # seconds
        },
        'sliding_window': {
            'window_size': 3600,  # 1 hour
            'max_requests': 1000
        }
    },
    'backoff_strategy': {
        'type': 'exponential',
        'base_delay': 1.0,
        'max_delay': 60.0,
        'multiplier': 2.0,
        'jitter': True
    },
    'circuit_breaker': {
        'enabled': True,
        'failure_threshold': 50,
        'recovery_timeout': 900,  # 15 minutes
        'half_open_max_calls': 5
    }
}

config = {
    'rate_limit': advanced_rate_limit
}
```

## Environment Variables

Configure sensitive data via environment variables:

```bash
# Authentication (when needed)
TIKTOK_API_KEY=your_api_key_here
TIKTOK_API_SECRET=your_api_secret_here
TIKTOK_ACCESS_TOKEN=your_access_token_here

# Proxy configuration
TIKTOK_PROXY_URL=http://proxy.example.com:8080
TIKTOK_PROXY_USERNAME=proxy_user
TIKTOK_PROXY_PASSWORD=proxy_pass

# Performance settings
TIKTOK_CACHE_TTL=1800
TIKTOK_MAX_CONCURRENT=5
TIKTOK_RATE_LIMIT_RPM=60

# Debugging
TIKTOK_DEBUG=true
TIKTOK_LOG_LEVEL=DEBUG
```

### Environment Variable Loading

```python
import os
from platforms.tiktok import TikTokHandler

# Load from environment
config = {
    'enable_caching': os.getenv('TIKTOK_CACHE_ENABLED', 'true').lower() == 'true',
    'cache_ttl': int(os.getenv('TIKTOK_CACHE_TTL', '1800')),
    'max_concurrent_operations': int(os.getenv('TIKTOK_MAX_CONCURRENT', '5')),
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': int(os.getenv('TIKTOK_RATE_LIMIT_RPM', '60'))
    }
}

# Load authentication if available
if os.getenv('TIKTOK_API_KEY'):
    config['enable_authentication'] = True
    config['credentials'] = {
        'api_key': os.getenv('TIKTOK_API_KEY'),
        'api_secret': os.getenv('TIKTOK_API_SECRET'),
        'access_token': os.getenv('TIKTOK_ACCESS_TOKEN')
    }

handler = TikTokHandler(config=config)
```

## Advanced Configuration

### Production Configuration

Recommended settings for production environments:

```python
production_config = {
    # Core settings
    'enable_caching': True,
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 10,
    
    # Cache optimization
    'cache_ttl': 3600,  # 1 hour for production
    'cache_max_size': 5000,  # Larger cache for production
    
    # Rate limiting for production
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 120,  # Higher limit for production
        'requests_per_hour': 5000,
        'adaptive_limiting': True,
        'circuit_breaker': {
            'enabled': True,
            'failure_threshold': 100,
            'recovery_timeout': 1800  # 30 minutes
        }
    },
    
    # Connection optimization
    'connection_config': {
        'connection_pool_size': 20,
        'keep_alive': True,
        'retry_attempts': 5
    },
    
    # Memory management
    'memory_config': {
        'max_memory_usage': 1024,  # 1GB
        'garbage_collection': {
            'enabled': True,
            'interval': 180  # 3 minutes
        }
    },
    
    # Enhanced session management
    'session_config': {
        'session_timeout': 7200,  # 2 hours
        'auto_refresh': True,
        'track_requests': True
    },
    
    # Monitoring and logging
    'monitoring': {
        'enabled': True,
        'performance_tracking': True,
        'error_reporting': True,
        'health_checks': True
    }
}

handler = TikTokHandler(config=production_config)
```

### Development Configuration

Optimized for development and testing:

```python
development_config = {
    # Relaxed settings for development
    'enable_caching': True,
    'cache_ttl': 300,  # 5 minutes for development
    'enable_concurrent_processing': False,  # Easier debugging
    
    # Verbose logging
    'logging': {
        'level': 'DEBUG',
        'enable_request_logging': True,
        'enable_performance_logging': True
    },
    
    # Relaxed rate limiting
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 30,  # Conservative for development
        'min_request_interval': 2.0,  # 2 seconds between requests
        'backoff_strategy': {
            'base_delay': 2.0  # Longer base delay
        }
    },
    
    # Quick timeouts for faster development cycles
    'connection_config': {
        'connection_timeout': 10,
        'read_timeout': 30,
        'retry_attempts': 2
    }
}

dev_handler = TikTokHandler(config=development_config)
```

### Testing Configuration

Configuration for automated testing:

```python
testing_config = {
    # Disable features that interfere with testing
    'enable_caching': False,  # Disable for predictable tests
    'enable_concurrent_processing': False,  # Sequential for testing
    
    # Fast timeouts for quick test execution
    'connection_config': {
        'connection_timeout': 5,
        'read_timeout': 10,
        'retry_attempts': 1
    },
    
    # Minimal rate limiting for tests
    'rate_limit': {
        'enabled': False  # Disable for testing
    },
    
    # Mock-friendly settings
    'session_config': {
        'track_requests': False,
        'cookies_file': None  # Don't persist cookies in tests
    }
}

test_handler = TikTokHandler(config=testing_config)
```

## Configuration Validation

### Validating Configuration

```python
def validate_config(config):
    """Validate TikTok handler configuration"""
    errors = []
    
    # Check required types
    if 'cache_ttl' in config and not isinstance(config['cache_ttl'], int):
        errors.append("cache_ttl must be an integer")
    
    if 'max_concurrent_operations' in config:
        if not isinstance(config['max_concurrent_operations'], int) or config['max_concurrent_operations'] < 1:
            errors.append("max_concurrent_operations must be a positive integer")
    
    # Check rate limiting
    if 'rate_limit' in config and config['rate_limit'].get('enabled'):
        rpm = config['rate_limit'].get('requests_per_minute', 0)
        if rpm < 1 or rpm > 1000:
            errors.append("requests_per_minute should be between 1 and 1000")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return True

# Usage
try:
    validate_config(config)
    handler = TikTokHandler(config=config)
except ValueError as e:
    print(f"Configuration error: {e}")
```

## Configuration Examples

### Example 1: High-Performance Setup

```python
high_performance_config = {
    'enable_caching': True,
    'cache_ttl': 3600,
    'cache_max_size': 10000,
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 20,
    'connection_config': {
        'connection_pool_size': 50,
        'keep_alive': True
    },
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 200,
        'adaptive_limiting': True
    }
}
```

### Example 2: Conservative Setup

```python
conservative_config = {
    'enable_caching': True,
    'cache_ttl': 1800,
    'enable_concurrent_processing': False,
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 30,
        'min_request_interval': 2.0
    },
    'connection_config': {
        'retry_attempts': 5,
        'retry_backoff': 2.0
    }
}
```

### Example 3: Proxy-Enabled Setup

```python
proxy_config = {
    'enable_caching': True,
    'proxy_config': {
        'enabled': True,
        'proxy_url': 'http://proxy.example.com:8080',
        'fallback_to_direct': True
    },
    'headers_config': {
        'user_agent_rotation': True,
        'rotation_interval': 50
    },
    'rate_limit': {
        'enabled': True,
        'requests_per_minute': 60
    }
}
```

## Best Practices

1. **Always enable rate limiting** to respect TikTok's servers
2. **Use caching** for better performance and reduced API calls
3. **Configure appropriate timeouts** based on your network conditions
4. **Monitor performance** and adjust settings based on usage patterns
5. **Use environment variables** for sensitive configuration
6. **Validate configuration** before initializing the handler
7. **Test configuration changes** in development environment first
8. **Document custom configurations** for team members

## Troubleshooting Configuration

Common configuration issues and solutions:

### Issue: High Memory Usage
```python
# Solution: Reduce cache size and enable garbage collection
config = {
    'cache_max_size': 500,  # Reduce from default
    'memory_config': {
        'garbage_collection': {
            'enabled': True,
            'interval': 120  # More frequent cleanup
        }
    }
}
```

### Issue: Rate Limiting Errors
```python
# Solution: Increase intervals and reduce rates
config = {
    'rate_limit': {
        'requests_per_minute': 30,  # Reduce from default
        'min_request_interval': 2.0,  # Increase interval
        'backoff_strategy': {
            'base_delay': 2.0  # Longer base delay
        }
    }
}
```

### Issue: Connection Timeouts
```python
# Solution: Increase timeouts and retries
config = {
    'connection_config': {
        'connection_timeout': 60,  # Increase timeout
        'read_timeout': 120,
        'retry_attempts': 5,  # More retries
        'retry_backoff': 2.0
    }
}
``` 