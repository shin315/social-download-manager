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