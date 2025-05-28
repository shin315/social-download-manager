# Service Layer Documentation

## Overview

The service layer provides a clean abstraction between the application controllers and the data layer, implementing clean architecture principles and dependency injection patterns.

## Architecture

```
┌─────────────────────┐
│   App Controller    │  ← Entry point, coordinates business operations
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Service Layer     │  ← Business logic, data validation, DTO conversion
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Repository Layer   │  ← Data access, database operations
└─────────────────────┘
```

## Components

### 1. Data Transfer Objects (DTOs)

DTOs provide type-safe data transfer between layers:

```python
from core.services import ContentDTO, DownloadRequestDTO

# Create content DTO
content = ContentDTO(
    url="https://youtube.com/watch?v=example",
    platform=PlatformType.YOUTUBE,
    status=ContentStatus.PENDING,
    title="Example Video"
)

# Convert to JSON for API responses
json_data = content.to_dict()
```

### 2. Service Interfaces

Clean interfaces define contracts for business operations:

```python
from core.services import IContentService

class CustomContentService(IContentService):
    async def create_content(self, content_dto: ContentDTO) -> ContentDTO:
        # Custom implementation
        pass
```

### 3. Service Registry

Dependency injection container for service management:

```python
from core.services import ServiceRegistry, get_service_registry

# Get global registry
registry = get_service_registry()

# Register services
registry.register_singleton(IContentService, ContentService)
registry.register_transient(IAnalyticsService, AnalyticsService)

# Retrieve services
content_service = registry.get_service(IContentService)
```

## Usage Patterns

### Basic Controller Integration

```python
from core.app_controller import get_app_controller

# Initialize application
controller = get_app_controller()
controller.initialize()

# Access services through controller
content_service = controller.get_content_service()
analytics_service = controller.get_analytics_service()
download_service = controller.get_download_service()
```

### Content Management Workflow

```python
async def handle_content_creation(url: str, platform: str):
    controller = get_app_controller()
    
    try:
        # Create content
        content = await controller.create_content_from_url(url, platform)
        if not content:
            return {"error": "Failed to create content"}
        
        # Start download
        download_result = await controller.start_download(
            content.url,
            {"quality": "720p", "format": "mp4"}
        )
        
        return {
            "content_id": content.id,
            "status": "download_started",
            "download_status": download_result.status
        }
        
    except Exception as e:
        controller.handle_error(e, "content_creation_workflow")
        return {"error": str(e)}
```

### Analytics Integration

```python
async def get_dashboard_data():
    controller = get_app_controller()
    
    # Get analytics overview
    analytics = await controller.get_analytics_overview()
    if not analytics:
        return {"error": "Analytics unavailable"}
    
    return analytics.to_dict()
```

### Custom Service Registration

```python
from core.services import configure_services

def setup_custom_services():
    registry = configure_services()
    
    # Register custom implementations
    registry.register_singleton(ICustomService, CustomServiceImpl)
    
    # Register factory for complex initialization
    registry.register_factory(
        IComplexService,
        lambda: ComplexService(dependencies...),
        ServiceLifetime.SINGLETON
    )
```

## Service Lifecycle Management

### Initialization Order

1. **Core Systems**: Configuration, Events, Database
2. **Service Registry**: Dependency injection container
3. **Service Registration**: Register all service implementations
4. **Service Resolution**: Services can depend on each other

### Shutdown Process

1. **Service Disposal**: Services with cleanup methods are called
2. **Registry Cleanup**: Clear all registered services
3. **Resource Cleanup**: Database connections, file handles, etc.

```python
# Proper application shutdown
controller = get_app_controller()
controller.shutdown()  # Automatically handles service disposal
```

## Error Handling

### Service-Level Errors

Services use domain-specific exceptions:

```python
from data.database.exceptions import EntityNotFoundError, DataValidationError

try:
    content = await content_service.create_content(invalid_dto)
except DataValidationError as e:
    # Handle validation errors
    return {"error": "Invalid data", "details": str(e)}
except EntityAlreadyExistsError as e:
    # Handle duplicate content
    return {"error": "Content already exists", "url": dto.url}
```

### Controller-Level Error Handling

Controllers provide centralized error handling:

```python
def custom_error_handler(error: Exception, context: str):
    # Custom error processing
    log_error_to_external_service(error, context)

controller = get_app_controller()
controller.add_error_handler(custom_error_handler)
```

## Testing Patterns

### Service Unit Testing

```python
import pytest
from unittest.mock import AsyncMock
from core.services import ContentService
from data.models.repositories import ContentRepository

@pytest.fixture
async def content_service():
    mock_repository = AsyncMock(spec=ContentRepository)
    return ContentService(mock_repository)

async def test_create_content(content_service):
    # Test service logic
    content_dto = ContentDTO(url="https://example.com")
    result = await content_service.create_content(content_dto)
    assert result is not None
```

### Integration Testing

```python
from tests.test_base import DatabaseTestCase

class TestServiceIntegration(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.controller = AppController()
        self.controller.initialize()
    
    async def test_end_to_end_workflow(self):
        # Test complete workflow with real database
        content = await self.controller.create_content_from_url(
            "https://example.com"
        )
        self.assertIsNotNone(content)
```

## Performance Considerations

### Service Caching

```python
from functools import lru_cache

class AnalyticsService(IAnalyticsService):
    @lru_cache(maxsize=128)
    async def get_platform_stats(self, platform: PlatformType):
        # Cache expensive calculations
        return await self._calculate_stats(platform)
```

### Async Best Practices

- Use `async`/`await` for I/O operations
- Prefer batch operations for multiple items
- Implement proper error handling for async operations

```python
async def process_multiple_urls(urls: List[str]):
    tasks = [
        controller.create_content_from_url(url)
        for url in urls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

## Configuration

### Service Configuration

Services can be configured through the application config:

```python
class ContentService(IContentService):
    def __init__(self, repository: ContentRepository = None):
        self._repository = repository or get_content_repository()
        self._config = get_config_manager().config
        
        # Use configuration for service behavior
        self._max_retries = self._config.content.max_retries
        self._timeout = self._config.content.operation_timeout
```

### Environment-Specific Services

```python
def configure_services():
    registry = get_service_registry()
    config = get_config_manager().config
    
    if config.environment == "development":
        registry.register_singleton(IContentService, DebugContentService)
    else:
        registry.register_singleton(IContentService, ContentService)
```

## Best Practices

1. **Interface Segregation**: Keep service interfaces focused and minimal
2. **Dependency Injection**: Always depend on interfaces, not implementations
3. **Error Handling**: Use domain-specific exceptions with proper context
4. **Resource Management**: Implement proper cleanup in service disposal
5. **Testing**: Write tests for both service logic and integration scenarios
6. **Documentation**: Document service contracts and expected behavior

## Common Issues and Solutions

### Service Not Available

```python
content_service = controller.get_content_service()
if not content_service:
    # Service not registered or initialization failed
    logger.error("Content service not available")
    return error_response("Service unavailable")
```

### Circular Dependencies

```python
# BAD: Services depending on each other
class ServiceA:
    def __init__(self, service_b: ServiceB):
        self.service_b = service_b

class ServiceB:
    def __init__(self, service_a: ServiceA):
        self.service_a = service_a

# GOOD: Use events or shared data layer
class ServiceA:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def do_work(self):
        result = await self.repository.save(data)
        self.event_bus.publish(Event("work_done", result))
```

### Memory Leaks

```python
class ServiceWithResources:
    def __init__(self):
        self.connections = []
        self.cache = {}
    
    def dispose(self):
        # Proper cleanup
        for conn in self.connections:
            conn.close()
        self.connections.clear()
        self.cache.clear()
```

## Migration Guide

### From Direct Repository Access

```python
# OLD: Direct repository usage in controllers
class OldController:
    def __init__(self):
        self.content_repo = get_content_repository()
    
    def create_content(self, url):
        model = ContentModel(url=url)
        return self.content_repo.save(model)

# NEW: Service layer usage
class NewController:
    def __init__(self):
        self.controller = get_app_controller()
    
    async def create_content(self, url):
        content_dto = ContentDTO(url=url)
        return await self.controller.create_content_from_url(url)
```

### Gradual Service Adoption

1. **Phase 1**: Introduce service interfaces alongside existing code
2. **Phase 2**: Implement services for new features
3. **Phase 3**: Migrate existing code to use services
4. **Phase 4**: Remove direct repository access from controllers

This documentation provides comprehensive guidance for using the service layer effectively in the Social Download Manager application. 