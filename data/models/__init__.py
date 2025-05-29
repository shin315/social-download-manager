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