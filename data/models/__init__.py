"""
Data Models for Social Download Manager v2.0

Contains abstract base models, concrete models for different content types,
and repository interfaces for data access.
"""

# Base models and utilities
from .base import (
    BaseModel, BaseEntity, ModelError, ValidationError,
    EntityId, Timestamp, JsonData
)

# Content models
from .content import (
    ContentModel, ContentType, ContentStatus, PlatformType,
    VideoContent, AudioContent, ImageContent, PostContent,
    QualityOption, ContentModelManager
)

# Download tracking models
from .downloads import (
    DownloadModel, DownloadStatus, DownloadProgress,
    DownloadSession, DownloadError, DownloadModelManager,
    DownloadSessionManager, DownloadErrorManager
)

# Repository interfaces and implementations
from .repositories import (
    IRepository, IContentRepository, RepositoryError,
    BaseRepository, ContentRepository, QueryBuilder,
    get_content_repository, register_repository
)

# Extended repository interfaces
from .repository_interfaces import (
    IDownloadRepository, IDownloadSessionRepository, IDownloadErrorRepository,
    IUserRepository, IConfigurationRepository, IAnalyticsRepository
)

# Download repository implementations
from .download_repositories import (
    DownloadRepository, DownloadSessionRepository, DownloadErrorRepository,
    get_download_repository, get_download_session_repository, 
    get_download_error_repository, register_download_repositories
)

# Advanced query capabilities
from .advanced_queries import (
    AdvancedQueryBuilder, QueryMethodsMixin, QueryOptimizer,
    DateRange, SortDirection, AggregateFunction
)

# Transaction-aware repositories
from .transaction_repository import (
    TransactionAwareRepositoryMixin, TransactionalRepository,
    UnitOfWork, transactional, requires_transaction
)

# Error management system
from .error_management import (
    ErrorSeverity, ErrorCategory, RecoveryStrategy,
    ErrorContext, ErrorInfo, DomainError,
    RepositoryValidationError, RepositoryDatabaseError, RepositoryConnectionError,
    RepositoryBusinessLogicError, RepositoryConfigurationError, RepositoryResourceError,
    IErrorHandler, ErrorManager, get_error_manager,
    handle_repository_errors, ErrorHandlingContext
)

# Performance optimization components
from .performance_optimizations import (
    ICacheProvider, LRUCache, TTLCache, RepositoryCache,
    BatchOperationManager, QueryOptimizer, PerformanceMonitor,
    PerformanceOptimizedRepository, CacheStrategy, PerformanceMetricType,
    performance_optimized, get_global_cache_provider, 
    get_global_performance_monitor, get_global_query_optimizer,
    set_global_cache_provider
) 