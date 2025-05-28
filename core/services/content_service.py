"""
Content Service Implementation

Provides business logic for content operations and acts as an intermediary
between the app controller and data layer.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from data.models.repositories import ContentRepository, get_content_repository
from data.models import ContentModel, ContentType, ContentStatus, PlatformType
from data.database.exceptions import (
    DatabaseError, RepositoryError, EntityNotFoundError,
    EntityAlreadyExistsError, DataValidationError
)

from .dtos import (
    ContentDTO, ContentSearchResultDTO, PlatformStatsDTO,
    content_model_to_dto, content_models_to_dtos, dto_to_content_model
)


class IContentService(ABC):
    """Interface for content service operations"""
    
    @abstractmethod
    async def create_content(self, content_dto: ContentDTO) -> ContentDTO:
        """Create new content"""
        pass
    
    @abstractmethod
    async def get_content_by_id(self, content_id: int) -> Optional[ContentDTO]:
        """Get content by ID"""
        pass
    
    @abstractmethod
    async def get_content_by_url(self, url: str) -> Optional[ContentDTO]:
        """Get content by URL"""
        pass
    
    @abstractmethod
    async def update_content(self, content_dto: ContentDTO) -> ContentDTO:
        """Update existing content"""
        pass
    
    @abstractmethod
    async def delete_content(self, content_id: int) -> bool:
        """Delete content by ID"""
        pass
    
    @abstractmethod
    async def search_content(self, query: str, limit: int = 50) -> List[ContentSearchResultDTO]:
        """Search content by query"""
        pass
    
    @abstractmethod
    async def get_content_by_platform(self, platform: PlatformType, limit: int = 50, offset: int = 0) -> List[ContentDTO]:
        """Get content by platform"""
        pass
    
    @abstractmethod
    async def get_content_by_status(self, status: ContentStatus, limit: int = 50, offset: int = 0) -> List[ContentDTO]:
        """Get content by status"""
        pass
    
    @abstractmethod
    async def get_platform_stats(self) -> Dict[PlatformType, PlatformStatsDTO]:
        """Get platform statistics"""
        pass
    
    @abstractmethod
    async def update_download_progress(self, content_id: int, progress: int) -> bool:
        """Update download progress for content"""
        pass
    
    @abstractmethod
    async def mark_download_completed(self, content_id: int, file_path: str, file_size: int) -> bool:
        """Mark download as completed"""
        pass
    
    @abstractmethod
    async def mark_download_failed(self, content_id: int, error_message: str) -> bool:
        """Mark download as failed"""
        pass


class ContentService(IContentService):
    """Content service implementation"""
    
    def __init__(self, repository: Optional[ContentRepository] = None):
        self._repository = repository or get_content_repository()
        self._logger = logging.getLogger(__name__)
    
    async def create_content(self, content_dto: ContentDTO) -> ContentDTO:
        """
        Create new content
        
        Args:
            content_dto: Content data transfer object
            
        Returns:
            Created content DTO
            
        Raises:
            EntityAlreadyExistsError: If content with URL already exists
            DataValidationError: If content data is invalid
        """
        try:
            # Check if content already exists by URL
            existing_content = await self.get_content_by_url(content_dto.url)
            if existing_content:
                raise EntityAlreadyExistsError(f"Content with URL {content_dto.url} already exists")
            
            # Convert DTO to model
            content_model = dto_to_content_model(content_dto)
            
            # Save to repository
            saved_model = self._repository.save(content_model)
            
            # Convert back to DTO
            result_dto = content_model_to_dto(saved_model)
            
            self._logger.info(f"Created content: {result_dto.id} - {result_dto.title}")
            return result_dto
            
        except (RepositoryError, DataValidationError) as e:
            self._logger.error(f"Failed to create content: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error creating content: {e}")
            raise RepositoryError(f"Failed to create content: {e}")
    
    async def get_content_by_id(self, content_id: int) -> Optional[ContentDTO]:
        """
        Get content by ID
        
        Args:
            content_id: Content ID
            
        Returns:
            Content DTO or None if not found
        """
        try:
            content_model = self._repository.find_by_id(content_id)
            if content_model:
                return content_model_to_dto(content_model)
            return None
            
        except Exception as e:
            self._logger.error(f"Failed to get content by ID {content_id}: {e}")
            raise RepositoryError(f"Failed to get content: {e}")
    
    async def get_content_by_url(self, url: str) -> Optional[ContentDTO]:
        """
        Get content by URL
        
        Args:
            url: Content URL
            
        Returns:
            Content DTO or None if not found
        """
        try:
            content_model = self._repository.find_by_url(url)
            if content_model:
                return content_model_to_dto(content_model)
            return None
            
        except Exception as e:
            self._logger.error(f"Failed to get content by URL {url}: {e}")
            raise RepositoryError(f"Failed to get content: {e}")
    
    async def update_content(self, content_dto: ContentDTO) -> ContentDTO:
        """
        Update existing content
        
        Args:
            content_dto: Content data transfer object with updated data
            
        Returns:
            Updated content DTO
            
        Raises:
            EntityNotFoundError: If content doesn't exist
        """
        try:
            if not content_dto.id:
                raise DataValidationError("Content ID is required for update")
            
            # Check if content exists
            existing_content = await self.get_content_by_id(content_dto.id)
            if not existing_content:
                raise EntityNotFoundError(f"Content with ID {content_dto.id} not found")
            
            # Convert DTO to model
            content_model = dto_to_content_model(content_dto)
            
            # Update in repository
            updated_model = self._repository.save(content_model)
            
            # Convert back to DTO
            result_dto = content_model_to_dto(updated_model)
            
            self._logger.info(f"Updated content: {result_dto.id} - {result_dto.title}")
            return result_dto
            
        except (RepositoryError, DataValidationError, EntityNotFoundError) as e:
            self._logger.error(f"Failed to update content: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error updating content: {e}")
            raise RepositoryError(f"Failed to update content: {e}")
    
    async def delete_content(self, content_id: int) -> bool:
        """
        Delete content by ID
        
        Args:
            content_id: Content ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            EntityNotFoundError: If content doesn't exist
        """
        try:
            # Check if content exists
            existing_content = await self.get_content_by_id(content_id)
            if not existing_content:
                raise EntityNotFoundError(f"Content with ID {content_id} not found")
            
            # Delete from repository
            result = self._repository.delete_by_id(content_id)
            
            if result:
                self._logger.info(f"Deleted content: {content_id}")
            
            return result
            
        except (RepositoryError, EntityNotFoundError) as e:
            self._logger.error(f"Failed to delete content: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error deleting content: {e}")
            raise RepositoryError(f"Failed to delete content: {e}")
    
    async def search_content(self, query: str, limit: int = 50) -> List[ContentSearchResultDTO]:
        """
        Search content by query
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of content search result DTOs
        """
        try:
            content_models = self._repository.search_content(query)
            
            # Convert to search result DTOs with relevance scoring
            results = []
            for model in content_models[:limit]:
                content_dto = content_model_to_dto(model)
                
                # Simple relevance scoring based on query matches
                relevance_score = self._calculate_relevance_score(query, model)
                matching_fields = self._get_matching_fields(query, model)
                snippet = self._generate_snippet(query, model)
                
                search_result = ContentSearchResultDTO(
                    content=content_dto,
                    relevance_score=relevance_score,
                    matching_fields=matching_fields,
                    snippet=snippet
                )
                results.append(search_result)
            
            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            self._logger.debug(f"Search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            self._logger.error(f"Failed to search content: {e}")
            raise RepositoryError(f"Failed to search content: {e}")
    
    async def get_content_by_platform(self, platform: PlatformType, limit: int = 50, offset: int = 0) -> List[ContentDTO]:
        """
        Get content by platform
        
        Args:
            platform: Platform type
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of content DTOs
        """
        try:
            content_models = self._repository.find_by_platform(platform)
            
            # Apply pagination
            paginated_models = content_models[offset:offset + limit]
            
            # Convert to DTOs
            result_dtos = content_models_to_dtos(paginated_models)
            
            self._logger.debug(f"Retrieved {len(result_dtos)} content items for platform {platform}")
            return result_dtos
            
        except Exception as e:
            self._logger.error(f"Failed to get content by platform: {e}")
            raise RepositoryError(f"Failed to get content by platform: {e}")
    
    async def get_content_by_status(self, status: ContentStatus, limit: int = 50, offset: int = 0) -> List[ContentDTO]:
        """
        Get content by status
        
        Args:
            status: Content status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of content DTOs
        """
        try:
            content_models = self._repository.find_by_status(status)
            
            # Apply pagination
            paginated_models = content_models[offset:offset + limit]
            
            # Convert to DTOs
            result_dtos = content_models_to_dtos(paginated_models)
            
            self._logger.debug(f"Retrieved {len(result_dtos)} content items with status {status}")
            return result_dtos
            
        except Exception as e:
            self._logger.error(f"Failed to get content by status: {e}")
            raise RepositoryError(f"Failed to get content by status: {e}")
    
    async def get_platform_stats(self) -> Dict[PlatformType, PlatformStatsDTO]:
        """
        Get platform statistics
        
        Returns:
            Dictionary of platform statistics
        """
        try:
            raw_stats = self._repository.get_platform_stats()
            
            # Convert to DTOs
            stats_dtos = {}
            for platform, stats in raw_stats.items():
                # Calculate additional metrics
                total = stats.get('total', 0)
                completed = stats.get('completed', 0)
                failed = stats.get('failed', 0)
                
                success_rate = (completed / total * 100) if total > 0 else 0.0
                
                stats_dto = PlatformStatsDTO(
                    platform=platform,
                    total_content=total,
                    completed_downloads=completed,
                    failed_downloads=failed,
                    pending_downloads=stats.get('pending', 0),
                    in_progress_downloads=stats.get('downloading', 0),
                    success_rate=success_rate,
                    # TODO: Add storage and performance statistics from database
                )
                
                stats_dtos[platform] = stats_dto
            
            self._logger.debug(f"Retrieved platform stats for {len(stats_dtos)} platforms")
            return stats_dtos
            
        except Exception as e:
            self._logger.error(f"Failed to get platform stats: {e}")
            raise RepositoryError(f"Failed to get platform stats: {e}")
    
    async def update_download_progress(self, content_id: int, progress: int) -> bool:
        """
        Update download progress for content
        
        Args:
            content_id: Content ID
            progress: Progress percentage (0-100)
            
        Returns:
            True if updated successfully
        """
        try:
            content_dto = await self.get_content_by_id(content_id)
            if not content_dto:
                raise EntityNotFoundError(f"Content with ID {content_id} not found")
            
            # Update progress and status
            updated_dto = ContentDTO(
                **{**content_dto.__dict__, 
                   'download_progress': progress,
                   'status': ContentStatus.DOWNLOADING if progress < 100 else content_dto.status,
                   'updated_at': datetime.now()}
            )
            
            await self.update_content(updated_dto)
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to update download progress: {e}")
            return False
    
    async def mark_download_completed(self, content_id: int, file_path: str, file_size: int) -> bool:
        """
        Mark download as completed
        
        Args:
            content_id: Content ID
            file_path: Path to downloaded file
            file_size: Size of downloaded file in bytes
            
        Returns:
            True if updated successfully
        """
        try:
            content_dto = await self.get_content_by_id(content_id)
            if not content_dto:
                raise EntityNotFoundError(f"Content with ID {content_id} not found")
            
            # Update content status and file information
            updated_dto = ContentDTO(
                **{**content_dto.__dict__,
                   'status': ContentStatus.COMPLETED,
                   'download_progress': 100,
                   'file_path': file_path,
                   'file_size': file_size,
                   'downloaded_at': datetime.now(),
                   'updated_at': datetime.now()}
            )
            
            await self.update_content(updated_dto)
            self._logger.info(f"Marked download completed: {content_id} -> {file_path}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to mark download completed: {e}")
            return False
    
    async def mark_download_failed(self, content_id: int, error_message: str) -> bool:
        """
        Mark download as failed
        
        Args:
            content_id: Content ID
            error_message: Error description
            
        Returns:
            True if updated successfully
        """
        try:
            content_dto = await self.get_content_by_id(content_id)
            if not content_dto:
                raise EntityNotFoundError(f"Content with ID {content_id} not found")
            
            # Update content status and error information
            updated_dto = ContentDTO(
                **{**content_dto.__dict__,
                   'status': ContentStatus.FAILED,
                   'error_message': error_message,
                   'retry_count': content_dto.retry_count + 1,
                   'updated_at': datetime.now()}
            )
            
            await self.update_content(updated_dto)
            self._logger.warning(f"Marked download failed: {content_id} - {error_message}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to mark download failed: {e}")
            return False
    
    def _calculate_relevance_score(self, query: str, model: ContentModel) -> float:
        """Calculate relevance score for search results"""
        score = 0.0
        query_lower = query.lower()
        
        # Title match (highest weight)
        if model.title and query_lower in model.title.lower():
            score += 3.0
        
        # Author match
        if model.author and query_lower in model.author.lower():
            score += 2.0
        
        # Description match
        if model.description and query_lower in model.description.lower():
            score += 1.0
        
        # URL match (lowest weight)
        if model.url and query_lower in model.url.lower():
            score += 0.5
        
        return score
    
    def _get_matching_fields(self, query: str, model: ContentModel) -> List[str]:
        """Get list of fields that match the query"""
        matching_fields = []
        query_lower = query.lower()
        
        if model.title and query_lower in model.title.lower():
            matching_fields.append('title')
        if model.author and query_lower in model.author.lower():
            matching_fields.append('author')
        if model.description and query_lower in model.description.lower():
            matching_fields.append('description')
        if model.url and query_lower in model.url.lower():
            matching_fields.append('url')
        
        return matching_fields
    
    def _generate_snippet(self, query: str, model: ContentModel) -> Optional[str]:
        """Generate a snippet showing the query context"""
        query_lower = query.lower()
        
        # Check description first
        if model.description and query_lower in model.description.lower():
            description = model.description
            index = description.lower().find(query_lower)
            if index != -1:
                start = max(0, index - 50)
                end = min(len(description), index + len(query) + 50)
                snippet = description[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(description):
                    snippet = snippet + "..."
                return snippet
        
        # Fallback to title
        if model.title:
            return model.title[:100] + ("..." if len(model.title) > 100 else "")
        
        return None


# Global instance
_content_service: Optional[ContentService] = None


def get_content_service() -> ContentService:
    """Get the global content service instance"""
    global _content_service
    if _content_service is None:
        _content_service = ContentService()
    return _content_service


def initialize_content_service(repository: Optional[ContentRepository] = None) -> ContentService:
    """Initialize the global content service instance"""
    global _content_service
    _content_service = ContentService(repository)
    return _content_service 