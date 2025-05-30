# Task 18 Data Integration Layer - Quick Reference
## Social Download Manager v2.0

### 🚀 Quick Start

```python
# Import global managers
from core.data_integration import (
    get_data_binding_manager,
    get_repository_state_manager,
    get_async_repository_manager,
    get_video_table_adapter,
    get_download_management_integrator,
    get_dataset_performance_manager
)

# Initialize repositories (from your existing code)
content_repo = get_content_repository()
download_repo = get_download_repository()
```

### 📊 Essential Integration Patterns

#### 1. Bind VideoTable to Repository (18.1 + 18.6)
```python
# Automatic data binding with real-time updates
binding_manager = get_data_binding_manager()
table_adapter = get_video_table_adapter(content_repo)

# Configure reactive binding
binding_manager.bind_repository_to_component(
    "video_table",
    content_repo,
    {"mode": "reactive", "auto_refresh": True}
)

# Get table data with filtering/sorting
table_data = await table_adapter.get_table_data(
    offset=0, limit=100,
    filters={"platform": "youtube"},
    sort_by="date_added"
)
```

#### 2. Platform Selection Integration (18.7)
```python
from core.data_integration.platform_selector_adapter import get_platform_selector_manager

manager = get_platform_selector_manager()
await manager.initialize(content_repo)

# Register UI callback
def update_ui(platform_data):
    for platform, stats in platform_data.items():
        print(f"{platform}: {stats['total']} videos")

manager.register_callback(update_ui)
manager.select_platforms(["youtube", "tiktok"])
```

#### 3. Download Management (18.8)
```python
integrator = get_download_management_integrator()
await integrator.initialize(download_repo, content_repo)

# Start download with progress tracking
def progress_callback(content_id, progress):
    print(f"Download {content_id}: {progress['percentage']}%")

success = await integrator.start_download(
    "content_123",
    progress_callback=progress_callback
)

# Batch downloads
results = await integrator.start_batch_download(["id1", "id2", "id3"])
```

#### 4. Async Operations (18.5)
```python
async_manager = get_async_repository_manager()

# Non-blocking repository operations
result = await async_manager.execute_async_operation(
    content_repo.get_all,
    component_id="video_table",
    show_progress=True,
    timeout_ms=30000
)
```

#### 5. Performance Optimization (18.9)
```python
perf_manager = get_dataset_performance_manager(content_repo)
await perf_manager.initialize()

# Optimized data loading with caching
data = await perf_manager.get_optimized_data(
    offset=0, limit=100,
    use_cache=True,
    loading_strategy="virtual"
)

# Performance report
report = perf_manager.get_performance_report()
print(f"Cache hit ratio: {report['global_metrics']['cache_hit_ratio']}%")
```

### 🔧 Common Configuration Patterns

#### Reactive Data Binding
```python
{
    "mode": "reactive",           # Real-time updates
    "auto_refresh": True,
    "refresh_interval": 30000,    # 30 seconds
    "cache_timeout": 60,
    "error_recovery": "retry_with_backoff"
}
```

#### Table Integration
```python
{
    "data_mode": "live",          # LIVE, CACHED, SNAPSHOT
    "cache_timeout": 300,
    "pagination_size": 100,
    "enable_virtual_scrolling": True,
    "debounce_ms": 500
}
```

#### Performance Optimization
```python
{
    "strategy": "adaptive",       # LRU, LFU, TTL, ADAPTIVE
    "max_size": 50000,
    "memory_limit_mb": 1024,
    "page_size": 100,
    "prefetch_pages": 3
}
```

### 🚨 Error Handling (18.4)

```python
from core.data_integration.repository_ui_error_integration import get_repository_ui_error_integrator

integrator = get_repository_ui_error_integrator()

# Register component error handling
integrator.register_component_error_handling(
    "video_table",
    {
        "show_dialogs": True,
        "use_status_bar": True,
        "auto_retry_attempts": 3,
        "fallback_strategy": "cache"
    }
)

# Handle errors gracefully
try:
    data = await content_repo.get_all()
except Exception as e:
    integrator.handle_repository_error(e, "video_table")
```

### 📋 State Synchronization (18.2)

```python
state_manager = get_repository_state_manager()

# Bidirectional sync configuration
state_manager.configure_component_sync(
    "platform_selector",
    content_repo,
    {
        "sync_mode": "bidirectional",
        "debounce_ms": 500,
        "optimistic_updates": True,
        "field_mappings": {
            "selected_platform": "platform_filter",
            "status_filter": "status"
        }
    }
)
```

### 🔔 Event Integration (18.3)

```python
from core.data_integration.repository_event_integration import get_repository_event_manager

event_manager = get_repository_event_manager()

# Subscribe to repository events
def content_handler(payload):
    print(f"Content updated: {payload.entity_id}")

event_manager.subscribe(
    "repository.entity.updated",
    content_handler,
    filters={"repository_type": "content"}
)

# Publish events
event_manager.publish_repository_event(
    "content",
    "repository.entity.created",
    {"entity_id": "new_content", "data": {...}}
)
```

### 🎯 Complete Workflow Example

```python
async def setup_video_management():
    """Complete integration setup example"""
    
    # 1. Initialize managers
    binding_manager = get_data_binding_manager()
    async_manager = get_async_repository_manager()
    table_adapter = get_video_table_adapter(content_repo)
    platform_manager = get_platform_selector_manager()
    download_integrator = get_download_management_integrator()
    
    # 2. Setup platform selector
    await platform_manager.initialize(content_repo)
    
    def on_platform_change(platform_data):
        # Update UI with platform statistics
        update_platform_ui(platform_data)
    
    platform_manager.register_callback(on_platform_change)
    
    # 3. Setup video table with reactive binding
    binding_manager.bind_repository_to_component(
        "video_table",
        content_repo,
        {"mode": "reactive", "auto_refresh": True}
    )
    
    # 4. Setup download management
    await download_integrator.initialize(download_repo, content_repo)
    
    def on_download_progress(content_id, progress):
        # Update download progress in UI
        update_download_progress_ui(content_id, progress)
    
    # 5. Load initial data asynchronously
    initial_data = await async_manager.execute_async_operation(
        table_adapter.get_table_data,
        component_id="video_table",
        show_progress=True,
        offset=0, limit=100
    )
    
    # 6. Setup event handling for cross-component communication
    event_manager = get_repository_event_manager()
    
    def on_content_change(payload):
        # Refresh table when content changes
        refresh_video_table()
    
    event_manager.subscribe(
        "repository.entity.updated",
        on_content_change,
        filters={"repository_type": "content"}
    )
    
    return {
        "table_data": initial_data,
        "managers": {
            "binding": binding_manager,
            "async": async_manager,
            "platform": platform_manager,
            "download": download_integrator
        }
    }

# Usage
setup_result = await setup_video_management()
```

### 🐛 Debugging & Troubleshooting

#### Enable Debug Logging
```python
import logging
logging.getLogger('data_integration').setLevel(logging.DEBUG)
```

#### Check Component Status
```python
# Data binding status
bindings = binding_manager.get_bindings()
print(f"Active bindings: {list(bindings.keys())}")

# Cache performance
cache_stats = perf_manager.cache.get_statistics()
print(f"Cache hit ratio: {cache_stats['cache_hit_ratio']}%")

# Event history
history = event_manager.get_event_history()
for event in history[-5:]:
    print(f"{event['timestamp']}: {event['event_type']}")
```

#### Performance Monitoring
```python
# Get comprehensive performance report
report = perf_manager.get_performance_report()
print("Performance Report:")
print(f"  Cache Hit Ratio: {report['global_metrics']['cache_hit_ratio']}%")
print(f"  Avg Load Time: {report['global_metrics']['avg_load_time_ms']}ms")
print(f"  Memory Usage: {report['memory_usage']['cache_memory_mb']}MB")
```

### 📚 Quick Reference Links

- **Full Documentation:** [task18-data-integration-guide.md](task18-data-integration-guide.md)
- **Architecture Overview:** See component interaction diagrams in full guide
- **API Reference:** Type hints and docstrings in component files
- **Test Examples:** `test_task18_integration_simple.py` for usage patterns

### 💡 Best Practices Summary

1. **Always use async operations** for repository calls
2. **Enable caching** for frequently accessed data
3. **Use reactive binding** for real-time UI updates
4. **Implement proper error handling** with user-friendly messages
5. **Monitor performance** with built-in metrics and reports
6. **Use event-driven patterns** for cross-component communication
7. **Enable virtual scrolling** for large datasets
8. **Configure debouncing** for rapid UI changes

---

This quick reference covers the most common usage patterns for the Task 18 Data Integration Layer. For detailed implementation guidance, refer to the full documentation guide. 