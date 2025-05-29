"""
Model Integration for Social Download Manager v2.0

Integration layer that ties together all models with relationship 
functionality, providing a unified interface for working with 
related models and maintaining data consistency.
"""

from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from datetime import datetime
import logging

from .pydantic_models import DatabaseEntity
from .core_models import (
    Platform, Content, ContentMetadata, Download, 
    DownloadSession, DownloadError, QualityOption,
    Tag, ContentTag, ApplicationSetting
)
from .platform_models import (
    TikTokContent, YouTubeContent, InstagramContent,
    TikTokMetadata, YouTubeMetadata, InstagramMetadata,
    PlatformModelFactory
)
from .enhanced_models import (
    Platform as EnhancedPlatform,
    Content as EnhancedContent,
    Download as EnhancedDownload,
    EnhancedPlatformModelFactory
)
from .relationships import (
    RelationshipManager, RelationshipMixin, RelationshipDescriptor,
    RelationshipConfig, RelationshipType, CascadeAction,
    get_relationship_manager, setup_model_relationships
)
from .validators import (
    URLValidator, BusinessRuleValidator,
    validate_status_transition
)

logger = logging.getLogger(__name__)


# =============================================================================
# INTEGRATED MODEL BASE CLASSES
# =============================================================================

class IntegratedModelMixin(RelationshipMixin):
    """Enhanced mixin that combines relationship and validation functionality"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up relationship manager if not already set
        if not self._relationship_manager:
            self.set_relationship_manager(get_relationship_manager())
    
    def save(self, validate_relationships: bool = True) -> bool:
        """Save model with optional relationship validation"""
        try:
            # Validate relationships if requested
            if validate_relationships:
                errors = self.validate_relationships()
                if errors:
                    raise ValueError(f"Relationship validation failed: {'; '.join(errors)}")
            
            # Update timestamps
            if hasattr(self, 'mark_updated'):
                self.mark_updated()
            
            # Here would be the actual database save operation
            logger.debug(f"Saved {type(self).__name__} with ID {getattr(self, 'id', 'new')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save {type(self).__name__}: {str(e)}")
            return False
    
    def delete(self, force: bool = False) -> bool:
        """Delete model with cascade handling"""
        try:
            if not force:
                # Validate referential integrity
                errors = self.validate_relationships()
                if errors:
                    raise ValueError(f"Cannot delete: {'; '.join(errors)}")
            
            # Execute cascade operations
            self.delete_with_cascade()
            
            logger.debug(f"Deleted {type(self).__name__} with ID {getattr(self, 'id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete {type(self).__name__}: {str(e)}")
            return False
    
    def refresh_from_db(self) -> bool:
        """Refresh model data from database"""
        try:
            # Here would be database refresh logic
            logger.debug(f"Refreshed {type(self).__name__} with ID {getattr(self, 'id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh {type(self).__name__}: {str(e)}")
            return False


# =============================================================================
# INTEGRATED CORE MODELS
# =============================================================================

class IntegratedPlatform(EnhancedPlatform, IntegratedModelMixin):
    """Platform model with full integration"""
    
    @property
    def content_items(self) -> List['IntegratedContent']:
        """Get all content items for this platform"""
        return self.get_related('platform_content')
    
    def get_content_count(self) -> int:
        """Get count of content items"""
        return len(self.content_items)
    
    def get_supported_content_types_list(self) -> List[str]:
        """Get supported content types as list"""
        import json
        try:
            return json.loads(self.supported_content_types)
        except json.JSONDecodeError:
            return []
    
    def add_supported_content_type(self, content_type: str) -> None:
        """Add a supported content type"""
        import json
        types = self.get_supported_content_types_list()
        if content_type not in types:
            types.append(content_type)
            self.supported_content_types = json.dumps(types)


class IntegratedContent(EnhancedContent, IntegratedModelMixin):
    """Content model with full integration"""
    
    @property
    def platform(self) -> Optional[IntegratedPlatform]:
        """Get the platform for this content"""
        # This would be loaded via relationship
        return None  # Placeholder
    
    @property
    def metadata_items(self) -> List[ContentMetadata]:
        """Get all metadata for this content"""
        return self.get_related('content_metadata')
    
    @property
    def downloads(self) -> List['IntegratedDownload']:
        """Get all downloads for this content"""
        return self.get_related('content_downloads')
    
    @property
    def quality_options(self) -> List[QualityOption]:
        """Get available quality options"""
        return self.get_related('content_quality_options')
    
    @property
    def tags(self) -> List[Tag]:
        """Get tags associated with this content"""
        content_tags = self.get_related('content_tags_content')
        return [ct.tag for ct in content_tags if ct.tag]
    
    def add_metadata(self, metadata_type: str, key: str, value: str, data_type: str = 'string') -> ContentMetadata:
        """Add metadata to content"""
        metadata = ContentMetadata(
            content_id=self.id,
            metadata_type=metadata_type,
            metadata_key=key,
            metadata_value=value,
            data_type=data_type
        )
        return metadata
    
    def get_metadata_value(self, key: str, metadata_type: Optional[str] = None) -> Optional[str]:
        """Get metadata value by key"""
        for metadata in self.metadata_items:
            if metadata.metadata_key == key:
                if metadata_type is None or metadata.metadata_type == metadata_type:
                    return metadata.metadata_value
        return None
    
    def create_download(self, output_directory: str, **kwargs) -> 'IntegratedDownload':
        """Create a new download for this content"""
        download_data = {
            'content_id': self.id,
            'output_directory': output_directory,
            **kwargs
        }
        
        # Validate download request
        content_data = self.model_dump()
        EnhancedPlatformModelFactory.validate_download_request(content_data, download_data)
        
        return IntegratedDownload(**download_data)
    
    def add_tag(self, tag: Union[Tag, str]) -> ContentTag:
        """Add a tag to this content"""
        if isinstance(tag, str):
            # Create or find tag by name
            tag_obj = Tag(name=tag, slug=tag.lower().replace(' ', '-'))
        else:
            tag_obj = tag
        
        content_tag = ContentTag(
            content_id=self.id,
            tag_id=tag_obj.id,
            assigned_by='user'
        )
        return content_tag
    
    def get_platform_specific_model(self):
        """Get platform-specific model instance"""
        if not self.platform:
            return self
        
        platform_name = self.platform.name
        model_class = PlatformModelFactory.get_content_model(platform_name)
        
        if model_class != Content:
            # Convert to platform-specific model
            data = self.model_dump()
            return model_class.model_validate(data)
        
        return self


class IntegratedDownload(EnhancedDownload, IntegratedModelMixin):
    """Download model with full integration"""
    
    @property
    def content(self) -> Optional[IntegratedContent]:
        """Get the content being downloaded"""
        # This would be loaded via relationship
        return None  # Placeholder
    
    @property
    def sessions(self) -> List[DownloadSession]:
        """Get all download sessions"""
        return self.get_related('download_sessions')
    
    @property
    def errors(self) -> List[DownloadError]:
        """Get all download errors"""
        return self.get_related('download_errors')
    
    @property
    def latest_session(self) -> Optional[DownloadSession]:
        """Get the most recent download session"""
        sessions = self.sessions
        if sessions:
            return max(sessions, key=lambda s: s.session_started_at or datetime.min)
        return None
    
    def start_session(self, session_type: str = 'standard') -> DownloadSession:
        """Start a new download session"""
        import uuid
        
        session = DownloadSession(
            download_id=self.id,
            session_uuid=str(uuid.uuid4()),
            session_type=session_type,
            session_status='active',
            session_started_at=datetime.now()
        )
        return session
    
    def add_error(self, error_type: str, error_message: str, **kwargs) -> DownloadError:
        """Add an error to this download"""
        error = DownloadError(
            download_id=self.id,
            error_type=error_type,
            error_message=error_message,
            occurred_at=datetime.now(),
            **kwargs
        )
        
        # Update download error count
        self.error_count += 1
        self.last_error_message = error_message
        
        return error
    
    def retry(self) -> bool:
        """Attempt to retry the download"""
        if not self.can_retry:
            return False
        
        # Reset status and increment retry count
        self.status = 'queued'
        self.retry_count += 1
        self.progress_percentage = 0
        
        return True
    
    def update_progress(self, percentage: float, speed_bps: Optional[int] = None) -> None:
        """Update download progress"""
        from decimal import Decimal
        
        self.progress_percentage = Decimal(str(min(100.0, max(0.0, percentage))))
        
        if speed_bps is not None:
            self.current_speed_bps = speed_bps
            
            # Update average speed (simple moving average)
            if self.average_speed_bps is None:
                self.average_speed_bps = speed_bps
            else:
                self.average_speed_bps = int((self.average_speed_bps + speed_bps) / 2)
    
    def complete(self, file_path: str, file_size: int) -> None:
        """Mark download as completed"""
        self.status = 'completed'
        self.progress_percentage = 100
        self.final_file_path = file_path
        self.actual_file_size = file_size
        self.completed_at = datetime.now()


# =============================================================================
# RELATIONSHIP PROPERTY DESCRIPTORS
# =============================================================================

def create_relationship_property(relationship_name: str, 
                                many: bool = False,
                                lazy: bool = True) -> property:
    """Create a property descriptor for a relationship"""
    
    def getter(self):
        """Get related objects"""
        related = self.get_related(relationship_name)
        
        if many and not isinstance(related, list):
            return [related] if related is not None else []
        elif not many and isinstance(related, list):
            return related[0] if related else None
        
        return related
    
    def setter(self, value):
        """Set related objects"""
        self.set_related(relationship_name, value)
    
    return property(getter, setter)


# =============================================================================
# MODEL FACTORY WITH INTEGRATION
# =============================================================================

class IntegratedModelFactory(EnhancedPlatformModelFactory):
    """Factory for creating integrated models"""
    
    # Integrated model mappings
    INTEGRATED_MODELS = {
        'platform': IntegratedPlatform,
        'content': IntegratedContent,
        'download': IntegratedDownload,
    }
    
    @classmethod
    def create_model(cls, model_type: str, data: Dict[str, Any], 
                    platform_name: Optional[str] = None) -> DatabaseEntity:
        """Create an integrated model instance"""
        
        if model_type == 'content' and platform_name:
            # Create platform-specific content model
            return cls.create_content_with_validation(platform_name, data)
        
        model_class = cls.INTEGRATED_MODELS.get(model_type)
        if not model_class:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return model_class.model_validate(data)
    
    @classmethod
    def create_content_with_relationships(cls, platform_name: str, 
                                        content_data: Dict[str, Any],
                                        metadata: Optional[List[Dict[str, Any]]] = None,
                                        tags: Optional[List[str]] = None) -> IntegratedContent:
        """Create content with related objects"""
        
        # Create main content object
        content = cls.create_content_with_validation(platform_name, content_data)
        
        # Add metadata if provided
        if metadata:
            for meta_data in metadata:
                content.add_metadata(**meta_data)
        
        # Add tags if provided
        if tags:
            for tag_name in tags:
                content.add_tag(tag_name)
        
        return content


# =============================================================================
# BULK OPERATIONS
# =============================================================================

class BulkOperations:
    """Helper for bulk operations with relationship management"""
    
    @staticmethod
    def bulk_create(instances: List[DatabaseEntity], 
                   validate_relationships: bool = True) -> List[bool]:
        """Bulk create instances with relationship validation"""
        results = []
        
        for instance in instances:
            if hasattr(instance, 'save'):
                success = instance.save(validate_relationships=validate_relationships)
                results.append(success)
            else:
                results.append(False)
        
        return results
    
    @staticmethod
    def bulk_delete(instances: List[DatabaseEntity], 
                   force: bool = False) -> List[bool]:
        """Bulk delete instances with cascade handling"""
        results = []
        
        # Validate all instances first if not forced
        if not force:
            for instance in instances:
                if hasattr(instance, 'validate_relationships'):
                    errors = instance.validate_relationships()
                    if errors:
                        raise ValueError(f"Cannot delete {type(instance).__name__}: {'; '.join(errors)}")
        
        # Delete instances
        for instance in instances:
            if hasattr(instance, 'delete'):
                success = instance.delete(force=force)
                results.append(success)
            else:
                results.append(False)
        
        return results
    
    @staticmethod
    def bulk_update_status(instances: List[DatabaseEntity], 
                          new_status: str,
                          validate_transitions: bool = True) -> List[bool]:
        """Bulk update status with validation"""
        results = []
        
        for instance in instances:
            if hasattr(instance, 'status'):
                # Validate status transition if requested
                if validate_transitions:
                    current_status = getattr(instance, 'status')
                    entity_type = 'content' if hasattr(instance, 'content_type') else 'download'
                    
                    is_valid, error = validate_status_transition(current_status, new_status, entity_type)
                    if not is_valid:
                        logger.warning(f"Invalid status transition: {error}")
                        results.append(False)
                        continue
                
                # Update status
                setattr(instance, 'status', new_status)
                if hasattr(instance, 'save'):
                    success = instance.save()
                    results.append(success)
                else:
                    results.append(True)
            else:
                results.append(False)
        
        return results


# =============================================================================
# RELATIONSHIP UTILITIES
# =============================================================================

def get_model_relationship_graph() -> Dict[str, Dict[str, Any]]:
    """Get detailed relationship graph for all models"""
    manager = get_relationship_manager()
    graph = {}
    
    for config in manager.relationships.values():
        source_name = config.source_model.__name__
        
        if source_name not in graph:
            graph[source_name] = {
                'outgoing': [],
                'incoming': []
            }
        
        graph[source_name]['outgoing'].append({
            'target': config.target_model.__name__,
            'relationship': config.name,
            'type': config.relationship_type.value,
            'cascade': config.on_delete.value
        })
        
        # Add incoming relationship
        target_name = config.target_model.__name__
        if target_name not in graph:
            graph[target_name] = {
                'outgoing': [],
                'incoming': []
            }
        
        graph[target_name]['incoming'].append({
            'source': source_name,
            'relationship': config.name,
            'type': config.relationship_type.value,
            'foreign_key': config.foreign_key_field
        })
    
    return graph


def validate_model_consistency(instances: List[DatabaseEntity]) -> Dict[str, Any]:
    """Validate consistency across multiple model instances"""
    errors = []
    warnings = []
    
    # Group instances by type
    instance_groups = {}
    for instance in instances:
        model_type = type(instance).__name__
        if model_type not in instance_groups:
            instance_groups[model_type] = []
        instance_groups[model_type].append(instance)
    
    # Validate each group
    for model_type, group_instances in instance_groups.items():
        # Check for relationship integrity
        relationship_errors = validate_relationship_integrity(group_instances)
        if relationship_errors:
            errors.extend(relationship_errors.values())
        
        # Check for business rule violations
        for instance in group_instances:
            if hasattr(instance, 'validate_relationships'):
                instance_errors = instance.validate_relationships()
                if instance_errors:
                    errors.extend(instance_errors)
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'instance_count': len(instances),
        'model_types': list(instance_groups.keys())
    }


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_model_integration():
    """Initialize the model integration system"""
    # Set up relationship manager for all integrated models
    manager = get_relationship_manager()
    
    IntegratedPlatform.set_relationship_manager(manager)
    IntegratedContent.set_relationship_manager(manager)
    IntegratedDownload.set_relationship_manager(manager)
    
    logger.info("Model integration system initialized")


# Initialize on import
initialize_model_integration() 