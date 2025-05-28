"""
Core Services Package

This package provides service layer interfaces and implementations for app controller integration.
Services act as intermediary between controllers and data layer.

Available Services:
- ContentService: Manages content operations
- AnalyticsService: Provides analytics data
- DownloadService: Handles download operations

Available DTOs:
- ContentDTO: Data transfer object for content
- AnalyticsDTO: Data transfer object for analytics
- DownloadRequestDTO: Data transfer object for download requests
"""

from .content_service import ContentService, IContentService
from .analytics_service import AnalyticsService, IAnalyticsService  
from .download_service import DownloadService, IDownloadService
from .dtos import (
    ContentDTO, AnalyticsDTO, DownloadRequestDTO, DownloadProgressDTO,
    PlatformStatsDTO, ContentSearchResultDTO
)
from .service_registry import ServiceRegistry, get_service_registry

__all__ = [
    # Service interfaces
    'IContentService',
    'IAnalyticsService', 
    'IDownloadService',
    
    # Service implementations
    'ContentService',
    'AnalyticsService',
    'DownloadService',
    
    # DTOs
    'ContentDTO',
    'AnalyticsDTO',
    'DownloadRequestDTO',
    'DownloadProgressDTO',
    'PlatformStatsDTO',
    'ContentSearchResultDTO',
    
    # Service registry
    'ServiceRegistry',
    'get_service_registry',
] 