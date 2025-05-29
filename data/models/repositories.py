"""
Repository Pattern Implementation for Social Download Manager v2.0

Provides repository interfaces and implementations for clean data access
abstraction with support for complex queries and custom operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Generic, TypeVar, Callable, Union
from datetime import datetime
import logging

from .base import BaseModel, BaseEntity, EntityId, ValidationError, ModelError
from .content import ContentModel, ContentType, ContentStatus, PlatformType
from .error_management import (
    get_error_manager, ErrorContext, ErrorHandlingContext,
    handle_repository_errors, RepositoryDatabaseError, RepositoryValidationError
)

T = TypeVar('T', bound=BaseEntity)


class RepositoryError(Exception):
    """Base exception for repository-related errors"""
    pass


class QueryBuilder:
    """Helper class for building complex database queries"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_fields = ["*"]
        self.where_conditions = []
        self.where_values = []
        self.order_by_clause = ""
        self.limit_clause = ""
        self.join_clauses = []
    
    def select(self, fields: Union[str, List[str]]) -> 'QueryBuilder':
        """Set SELECT fields"""
        if isinstance(fields, str):
            self.select_fields = [fields]
        else:
            self.select_fields = fields
        return self
    
    def where(self, condition: str, *values: Any) -> 'QueryBuilder':
        """Add WHERE condition"""
        self.where_conditions.append(condition)
        self.where_values.extend(values)
        return self
    
    def where_equals(self, field: str, value: Any) -> 'QueryBuilder':
        """Add WHERE field = value condition"""
        self.where_conditions.append(f"{field} = ?")
        self.where_values.append(value)
        return self
    
    def where_in(self, field: str, values: List[Any]) -> 'QueryBuilder':
        """Add WHERE field IN (...) condition"""
        placeholders = ', '.join(['?' for _ in values])
        self.where_conditions.append(f"{field} IN ({placeholders})")
        self.where_values.extend(values)
        return self
    
    def where_like(self, field: str, pattern: str) -> 'QueryBuilder':
        """Add WHERE field LIKE pattern condition"""
        self.where_conditions.append(f"{field} LIKE ?")
        self.where_values.append(pattern)
        return self
    
    def where_between(self, field: str, start: Any, end: Any) -> 'QueryBuilder':
        """Add WHERE field BETWEEN start AND end condition"""
        self.where_conditions.append(f"{field} BETWEEN ? AND ?")
        self.where_values.extend([start, end])
        return self
    
    def where_not_deleted(self) -> 'QueryBuilder':
        """Add WHERE is_deleted = 0 condition"""
        return self.where_equals("is_deleted", 0)
    
    def order_by(self, field: str, direction: str = "ASC") -> 'QueryBuilder':
        """Set ORDER BY clause"""
        direction = direction.upper()
        if direction not in ["ASC", "DESC"]:
            direction = "ASC"
        self.order_by_clause = f"ORDER BY {field} {direction}"
        return self
    
    def limit(self, count: int, offset: int = 0) -> 'QueryBuilder':
        """Set LIMIT clause"""
        if offset > 0:
            self.limit_clause = f"LIMIT {count} OFFSET {offset}"
        else:
            self.limit_clause = f"LIMIT {count}"
        return self
    
    def build(self) -> tuple:
        """Build the final SQL query and parameters"""
        # Build SELECT
        select_clause = f"SELECT {', '.join(self.select_fields)}"
        
        # Build FROM
        from_clause = f"FROM {self.table_name}"
        
        # Build WHERE
        where_clause = ""
        if self.where_conditions:
            where_clause = f"WHERE {' AND '.join(self.where_conditions)}"
        
        # Combine all clauses
        query_parts = [select_clause, from_clause]
        query_parts.extend(self.join_clauses)
        if where_clause:
            query_parts.append(where_clause)
        if self.order_by_clause:
            query_parts.append(self.order_by_clause)
        if self.limit_clause:
            query_parts.append(self.limit_clause)
        
        query = " ".join(query_parts)
        return query, self.where_values


class IRepository(ABC, Generic[T]):
    """
    Generic repository interface defining common data access methods
    
    Provides standard CRUD operations and query building capabilities
    with proper abstraction from the underlying data storage.
    """
    
    @abstractmethod
    def save(self, entity: T) -> Optional[T]:
        """Save entity (insert or update)"""
        pass
    
    @abstractmethod
    def find_by_id(self, entity_id: EntityId) -> Optional[T]:
        """Find entity by ID"""
        pass
    
    @abstractmethod
    def find_all(self, include_deleted: bool = False) -> List[T]:
        """Find all entities"""
        pass
    
    @abstractmethod
    def delete(self, entity_id: EntityId, soft_delete: bool = True) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    def exists(self, entity_id: EntityId) -> bool:
        """Check if entity exists"""
        pass
    
    @abstractmethod
    def count(self, include_deleted: bool = False) -> int:
        """Count total entities"""
        pass
    
    @abstractmethod
    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Find entities by criteria"""
        pass
    
    @abstractmethod
    def query(self) -> QueryBuilder:
        """Get query builder for complex queries"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: List[Any] = None) -> List[T]:
        """Execute custom query and return entities"""
        pass


class IContentRepository(IRepository[ContentModel]):
    """
    Repository interface for content entities
    
    Extends base repository with content-specific operations
    for social media content management.
    """
    
    @abstractmethod
    def find_by_url(self, url: str) -> Optional[ContentModel]:
        """Find content by URL"""
        pass
    
    @abstractmethod
    def find_by_platform_id(self, platform: PlatformType, platform_id: str) -> Optional[ContentModel]:
        """Find content by platform and platform ID"""
        pass
    
    @abstractmethod
    def find_by_status(self, status: ContentStatus) -> List[ContentModel]:
        """Find content by status"""
        pass
    
    @abstractmethod
    def find_by_platform(self, platform: PlatformType) -> List[ContentModel]:
        """Find content by platform"""
        pass
    
    @abstractmethod
    def find_by_content_type(self, content_type: ContentType) -> List[ContentModel]:
        """Find content by type"""
        pass
    
    @abstractmethod
    def find_by_author(self, author: str) -> List[ContentModel]:
        """Find content by author"""
        pass
    
    @abstractmethod
    def find_downloaded_content(self) -> List[ContentModel]:
        """Find all downloaded content"""
        pass
    
    @abstractmethod
    def find_failed_downloads(self) -> List[ContentModel]:
        """Find all failed downloads"""
        pass
    
    @abstractmethod
    def find_in_progress_downloads(self) -> List[ContentModel]:
        """Find all downloads in progress"""
        pass
    
    @abstractmethod
    def search_content(self, search_term: str) -> List[ContentModel]:
        """Search content by title, description, or author"""
        pass
    
    @abstractmethod
    def get_download_stats(self) -> Dict[str, int]:
        """Get download statistics by status"""
        pass
    
    @abstractmethod
    def get_platform_stats(self) -> Dict[str, int]:
        """Get statistics by platform"""
        pass
    
    @abstractmethod
    def find_recent_content(self, days: int = 7) -> List[ContentModel]:
        """Find content created in recent days"""
        pass
    
    @abstractmethod
    def find_large_files(self, min_size_mb: int = 100) -> List[ContentModel]:
        """Find content files larger than specified size"""
        pass


class BaseRepository(IRepository[T]):
    """
    Base repository implementation providing common functionality
    
    Implements standard CRUD operations using the model layer
    and provides query building capabilities.
    """
    
    def __init__(self, model_manager):
        """
        Initialize repository with model manager
        
        Args:
            model_manager: Model manager instance for database operations
        """
        self._model = model_manager
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @handle_repository_errors("save_entity")
    def save(self, entity: T) -> Optional[T]:
        """Save entity using model layer with comprehensive error handling"""
        with ErrorHandlingContext("save_entity", entity.id, entity.__class__.__name__):
            return self._model.save(entity)
    
    @handle_repository_errors("find_by_id")
    def find_by_id(self, entity_id: EntityId) -> Optional[T]:
        """Find entity by ID with error handling"""
        with ErrorHandlingContext("find_by_id", entity_id):
            return self._model.find_by_id(entity_id)
    
    @handle_repository_errors("find_all")
    def find_all(self, include_deleted: bool = False) -> List[T]:
        """Find all entities with error handling"""
        with ErrorHandlingContext("find_all"):
            return self._model.find_all(include_deleted)
    
    @handle_repository_errors("delete_entity")
    def delete(self, entity_id: EntityId, soft_delete: bool = True) -> bool:
        """Delete entity with error handling"""
        with ErrorHandlingContext("delete_entity", entity_id):
            return self._model.delete(entity_id, soft_delete)
    
    @handle_repository_errors("entity_exists")
    def exists(self, entity_id: EntityId) -> bool:
        """Check if entity exists with error handling"""
        with ErrorHandlingContext("entity_exists", entity_id):
            return self._model.exists(entity_id)
    
    @handle_repository_errors("count_entities")
    def count(self, include_deleted: bool = False) -> int:
        """Count entities with error handling"""
        with ErrorHandlingContext("count_entities"):
            return self._model.count(include_deleted)
    
    @handle_repository_errors("find_by_criteria")
    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Find entities by criteria with error handling"""
        with ErrorHandlingContext("find_by_criteria"):
            return self._model.find_by_criteria(criteria)
    
    def query(self) -> QueryBuilder:
        """Get query builder for complex queries"""
        return QueryBuilder(self._model.get_table_name())
    
    @handle_repository_errors("execute_query")
    def execute_query(self, query: str, params: List[Any] = None) -> List[T]:
        """Execute custom query with error handling"""
        with ErrorHandlingContext("execute_query"):
            if params is None:
                params = []
            
            try:
                connection = self._model._get_connection()
                try:
                    cursor = connection.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    cursor.close()
                    
                    # Convert rows to entities
                    entities = []
                    for row in rows:
                        try:
                            entity = self._model.get_entity_class().from_row(row)
                            entities.append(entity)
                        except Exception as e:
                            self._logger.warning(f"Failed to convert row to entity: {e}")
                            continue
                    
                    return entities
                    
                finally:
                    self._model._return_connection(connection)
                    
            except Exception as e:
                error_manager = get_error_manager()
                context = ErrorContext("execute_query")
                error_info = error_manager.handle_error(e, context)
                raise RepositoryDatabaseError(error_info.message, e, context)


class ContentRepository(BaseRepository[ContentModel], IContentRepository):
    """
    Content repository implementation
    
    Provides content-specific data access operations with
    optimized queries for social media content management.
    """
    
    def find_by_url(self, url: str) -> Optional[ContentModel]:
        """Find content by URL"""
        try:
            return self._model.find_by_url(url)
        except Exception as e:
            self._logger.error(f"Failed to find content by URL: {e}")
            raise RepositoryError(f"Find by URL failed: {e}")
    
    def find_by_platform_id(self, platform: PlatformType, platform_id: str) -> Optional[ContentModel]:
        """Find content by platform and platform ID"""
        try:
            return self._model.find_by_platform_id(platform, platform_id)
        except Exception as e:
            self._logger.error(f"Failed to find content by platform ID: {e}")
            raise RepositoryError(f"Find by platform ID failed: {e}")
    
    def find_by_status(self, status: ContentStatus) -> List[ContentModel]:
        """Find content by status"""
        try:
            return self._model.find_by_status(status)
        except Exception as e:
            self._logger.error(f"Failed to find content by status: {e}")
            raise RepositoryError(f"Find by status failed: {e}")
    
    def find_by_platform(self, platform: PlatformType) -> List[ContentModel]:
        """Find content by platform"""
        try:
            return self._model.find_by_platform(platform)
        except Exception as e:
            self._logger.error(f"Failed to find content by platform: {e}")
            raise RepositoryError(f"Find by platform failed: {e}")
    
    def find_by_content_type(self, content_type: ContentType) -> List[ContentModel]:
        """Find content by type"""
        try:
            return self.find_by_criteria({'content_type': content_type.value})
        except Exception as e:
            self._logger.error(f"Failed to find content by type: {e}")
            raise RepositoryError(f"Find by content type failed: {e}")
    
    def find_by_author(self, author: str) -> List[ContentModel]:
        """Find content by author"""
        try:
            return self.find_by_criteria({'author': author})
        except Exception as e:
            self._logger.error(f"Failed to find content by author: {e}")
            raise RepositoryError(f"Find by author failed: {e}")
    
    def find_downloaded_content(self) -> List[ContentModel]:
        """Find all downloaded content"""
        return self.find_by_status(ContentStatus.COMPLETED)
    
    def find_failed_downloads(self) -> List[ContentModel]:
        """Find all failed downloads"""
        return self.find_by_status(ContentStatus.FAILED)
    
    def find_in_progress_downloads(self) -> List[ContentModel]:
        """Find all downloads in progress"""
        in_progress_statuses = [
            ContentStatus.DOWNLOADING,
            ContentStatus.PROCESSING,
            ContentStatus.PENDING
        ]
        
        results = []
        for status in in_progress_statuses:
            results.extend(self.find_by_status(status))
        return results
    
    def search_content(self, search_term: str) -> List[ContentModel]:
        """Search content by title, description, or author"""
        try:
            # Build search query with LIKE conditions
            query, params = (self.query()
                           .where_not_deleted()
                           .where("(title LIKE ? OR description LIKE ? OR author LIKE ?)",
                                  f"%{search_term}%", f"%{search_term}%", f"%{search_term}%")
                           .order_by("created_at", "DESC")
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to search content: {e}")
            raise RepositoryError(f"Content search failed: {e}")
    
    def get_download_stats(self) -> Dict[str, int]:
        """Get download statistics by status"""
        try:
            return self._model.get_download_stats()
        except Exception as e:
            self._logger.error(f"Failed to get download stats: {e}")
            raise RepositoryError(f"Get download stats failed: {e}")
    
    def get_platform_stats(self) -> Dict[str, int]:
        """Get statistics by platform"""
        try:
            stats = {}
            for platform in PlatformType:
                count = len(self.find_by_platform(platform))
                if count > 0:  # Only include platforms with content
                    stats[platform.value] = count
            return stats
        except Exception as e:
            self._logger.error(f"Failed to get platform stats: {e}")
            raise RepositoryError(f"Get platform stats failed: {e}")
    
    def find_recent_content(self, days: int = 7) -> List[ContentModel]:
        """Find content created in recent days"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()
            
            query, params = (self.query()
                           .where_not_deleted()
                           .where("created_at >= ?", cutoff_iso)
                           .order_by("created_at", "DESC")
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to find recent content: {e}")
            raise RepositoryError(f"Find recent content failed: {e}")
    
    def find_large_files(self, min_size_mb: int = 100) -> List[ContentModel]:
        """Find content files larger than specified size"""
        try:
            min_size_bytes = min_size_mb * 1024 * 1024  # Convert MB to bytes
            
            query, params = (self.query()
                           .where_not_deleted()
                           .where("file_size >= ?", min_size_bytes)
                           .where("file_size IS NOT NULL")
                           .order_by("file_size", "DESC")
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to find large files: {e}")
            raise RepositoryError(f"Find large files failed: {e}")


# Repository factory and registry
class RepositoryRegistry:
    """Registry for repository instances following singleton pattern"""
    
    def __init__(self):
        self._repositories = {}
        self._model_managers = {}
    
    def register_model_manager(self, entity_type: type, model_manager):
        """Register model manager for entity type"""
        self._model_managers[entity_type] = model_manager
    
    def get_repository(self, repository_class: type, entity_type: type):
        """Get repository instance (singleton)"""
        repo_key = (repository_class, entity_type)
        
        if repo_key not in self._repositories:
            if entity_type not in self._model_managers:
                raise RepositoryError(f"No model manager registered for {entity_type}")
            
            model_manager = self._model_managers[entity_type]
            self._repositories[repo_key] = repository_class(model_manager)
        
        return self._repositories[repo_key]


# Global repository registry
_repository_registry = RepositoryRegistry()


def get_content_repository() -> IContentRepository:
    """Get content repository instance"""
    from .content import ContentModelManager
    
    # Register model manager if not already registered
    if ContentModel not in _repository_registry._model_managers:
        _repository_registry.register_model_manager(ContentModel, ContentModelManager())
    
    return _repository_registry.get_repository(ContentRepository, ContentModel)


def register_repository(entity_type: type, model_manager) -> None:
    """Register a model manager for an entity type"""
    _repository_registry.register_model_manager(entity_type, model_manager) 