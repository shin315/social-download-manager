"""
Model Relationship Management for Social Download Manager v2.0

Comprehensive system for managing relationships between models,
including foreign key relationships, cascading operations, and
referential integrity enforcement.
"""

from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Union, Type, TypeVar, Generic,
    Set, Tuple, Callable, Iterator
)
from enum import Enum
from dataclasses import dataclass
import logging
from weakref import WeakKeyDictionary

logger = logging.getLogger(__name__)

# Type aliases
ModelType = TypeVar('ModelType')
RelatedModelType = TypeVar('RelatedModelType')


# =============================================================================
# RELATIONSHIP TYPES AND CONFIGURATION
# =============================================================================

class RelationshipType(str, Enum):
    """Types of relationships between models"""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many" 
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class CascadeAction(str, Enum):
    """Actions to take when parent is deleted/updated"""
    RESTRICT = "restrict"    # Prevent deletion if children exist
    CASCADE = "cascade"      # Delete children when parent is deleted
    SET_NULL = "set_null"    # Set foreign key to NULL
    SET_DEFAULT = "set_default"  # Set foreign key to default value
    NO_ACTION = "no_action"  # Do nothing


@dataclass
class RelationshipConfig:
    """Configuration for a relationship between models"""
    name: str
    source_model: Type
    target_model: Type
    relationship_type: RelationshipType
    foreign_key_field: str
    related_field: Optional[str] = None
    on_delete: CascadeAction = CascadeAction.RESTRICT
    on_update: CascadeAction = CascadeAction.NO_ACTION
    lazy_loading: bool = True
    nullable: bool = True
    back_reference: Optional[str] = None


# =============================================================================
# RELATIONSHIP DESCRIPTOR
# =============================================================================

class RelationshipDescriptor:
    """Descriptor for handling model relationships"""
    
    def __init__(self, config: RelationshipConfig):
        self.config = config
        self._cache = WeakKeyDictionary()
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        # Check cache first
        if instance in self._cache:
            return self._cache[instance]
        
        # Load related objects
        related_objects = self._load_related(instance)
        self._cache[instance] = related_objects
        return related_objects
    
    def __set__(self, instance, value):
        # Validate the relationship assignment
        self._validate_assignment(instance, value)
        self._cache[instance] = value
    
    def _load_related(self, instance):
        """Load related objects based on relationship type"""
        if self.config.lazy_loading:
            return LazyRelationshipLoader(self.config, instance)
        else:
            return self._eager_load(instance)
    
    def _eager_load(self, instance):
        """Eagerly load related objects"""
        # This would integrate with the database layer
        # For now, return placeholder
        return None
    
    def _validate_assignment(self, instance, value):
        """Validate relationship assignment"""
        if value is None and not self.config.nullable:
            raise ValueError(f"Relationship {self.config.name} cannot be null")
        
        if value is not None:
            if self.config.relationship_type in [RelationshipType.ONE_TO_ONE, RelationshipType.MANY_TO_ONE]:
                if not isinstance(value, self.config.target_model):
                    raise TypeError(f"Expected {self.config.target_model.__name__}, got {type(value).__name__}")
            elif self.config.relationship_type in [RelationshipType.ONE_TO_MANY, RelationshipType.MANY_TO_MANY]:
                if not isinstance(value, (list, RelatedObjectsList)):
                    raise TypeError(f"Expected list or RelatedObjectsList, got {type(value).__name__}")


# =============================================================================
# LAZY LOADING
# =============================================================================

class LazyRelationshipLoader:
    """Lazy loader for relationships"""
    
    def __init__(self, config: RelationshipConfig, instance):
        self.config = config
        self.instance = instance
        self._loaded = False
        self._data = None
    
    def __iter__(self):
        if not self._loaded:
            self._load_data()
        
        if isinstance(self._data, list):
            return iter(self._data)
        else:
            return iter([self._data] if self._data is not None else [])
    
    def __getitem__(self, key):
        if not self._loaded:
            self._load_data()
        
        if isinstance(self._data, list):
            return self._data[key]
        else:
            if key == 0 and self._data is not None:
                return self._data
            raise IndexError("Index out of range")
    
    def __len__(self):
        if not self._loaded:
            self._load_data()
        
        if isinstance(self._data, list):
            return len(self._data)
        else:
            return 1 if self._data is not None else 0
    
    def _load_data(self):
        """Load the actual data"""
        # This would integrate with the database layer
        # For now, simulate loading
        self._data = self._simulate_load()
        self._loaded = True
    
    def _simulate_load(self):
        """Simulate loading related objects"""
        # Placeholder implementation
        return [] if self.config.relationship_type in [RelationshipType.ONE_TO_MANY, RelationshipType.MANY_TO_MANY] else None


# =============================================================================
# RELATED OBJECTS COLLECTION
# =============================================================================

class RelatedObjectsList(list):
    """Custom list for managing related objects with relationship awareness"""
    
    def __init__(self, parent_instance, relationship_config: RelationshipConfig):
        super().__init__()
        self.parent_instance = parent_instance
        self.config = relationship_config
        self._pending_adds = set()
        self._pending_removes = set()
    
    def append(self, item):
        """Add item with relationship validation"""
        self._validate_item(item)
        super().append(item)
        self._pending_adds.add(item)
        self._set_back_reference(item)
    
    def remove(self, item):
        """Remove item with relationship handling"""
        super().remove(item)
        self._pending_removes.add(item)
        self._clear_back_reference(item)
    
    def extend(self, items):
        """Extend with multiple items"""
        for item in items:
            self.append(item)
    
    def clear(self):
        """Clear all items"""
        for item in list(self):
            self.remove(item)
    
    def _validate_item(self, item):
        """Validate that item is correct type"""
        if not isinstance(item, self.config.target_model):
            raise TypeError(f"Expected {self.config.target_model.__name__}, got {type(item).__name__}")
    
    def _set_back_reference(self, item):
        """Set back reference on related item"""
        if self.config.back_reference:
            setattr(item, self.config.back_reference, self.parent_instance)
    
    def _clear_back_reference(self, item):
        """Clear back reference on related item"""
        if self.config.back_reference:
            setattr(item, self.config.back_reference, None)
    
    def get_pending_changes(self):
        """Get pending add/remove operations"""
        return {
            'adds': list(self._pending_adds),
            'removes': list(self._pending_removes)
        }
    
    def commit_changes(self):
        """Mark changes as committed"""
        self._pending_adds.clear()
        self._pending_removes.clear()


# =============================================================================
# RELATIONSHIP MANAGER
# =============================================================================

class RelationshipManager:
    """Central manager for all model relationships"""
    
    def __init__(self):
        self.relationships: Dict[str, RelationshipConfig] = {}
        self.model_relationships: Dict[Type, List[RelationshipConfig]] = {}
        self._cascade_handlers: Dict[CascadeAction, Callable] = {
            CascadeAction.RESTRICT: self._handle_restrict,
            CascadeAction.CASCADE: self._handle_cascade,
            CascadeAction.SET_NULL: self._handle_set_null,
            CascadeAction.SET_DEFAULT: self._handle_set_default,
            CascadeAction.NO_ACTION: self._handle_no_action,
        }
    
    def register_relationship(self, config: RelationshipConfig):
        """Register a relationship configuration"""
        self.relationships[config.name] = config
        
        # Add to model relationships
        if config.source_model not in self.model_relationships:
            self.model_relationships[config.source_model] = []
        self.model_relationships[config.source_model].append(config)
        
        logger.debug(f"Registered relationship: {config.name}")
    
    def get_relationships_for_model(self, model_class: Type) -> List[RelationshipConfig]:
        """Get all relationships for a model"""
        return self.model_relationships.get(model_class, [])
    
    def get_relationship(self, name: str) -> Optional[RelationshipConfig]:
        """Get relationship configuration by name"""
        return self.relationships.get(name)
    
    def validate_referential_integrity(self, instance, operation: str = 'delete') -> List[str]:
        """Validate referential integrity for an operation"""
        errors = []
        model_class = type(instance)
        
        for config in self.get_relationships_for_model(model_class):
            if operation == 'delete' and config.on_delete == CascadeAction.RESTRICT:
                # Check if there are related objects that would prevent deletion
                related_count = self._count_related_objects(instance, config)
                if related_count > 0:
                    errors.append(f"Cannot delete {model_class.__name__}: {related_count} related {config.target_model.__name__} objects exist")
        
        return errors
    
    def execute_cascade_operations(self, instance, operation: str = 'delete'):
        """Execute cascade operations for an instance"""
        model_class = type(instance)
        
        for config in self.get_relationships_for_model(model_class):
            if operation == 'delete':
                handler = self._cascade_handlers[config.on_delete]
                handler(instance, config)
            elif operation == 'update':
                handler = self._cascade_handlers[config.on_update]
                handler(instance, config)
    
    def _count_related_objects(self, instance, config: RelationshipConfig) -> int:
        """Count related objects for an instance"""
        # This would integrate with the database layer
        # For now, return 0 as placeholder
        return 0
    
    def _handle_restrict(self, instance, config: RelationshipConfig):
        """Handle RESTRICT cascade action"""
        errors = self.validate_referential_integrity(instance, 'delete')
        if errors:
            raise ValueError(f"Referential integrity violation: {'; '.join(errors)}")
    
    def _handle_cascade(self, instance, config: RelationshipConfig):
        """Handle CASCADE cascade action"""
        # Get related objects and delete them
        related_objects = self._get_related_objects(instance, config)
        for obj in related_objects:
            # This would call the delete method on the object
            pass
    
    def _handle_set_null(self, instance, config: RelationshipConfig):
        """Handle SET_NULL cascade action"""
        if not config.nullable:
            raise ValueError(f"Cannot set {config.foreign_key_field} to NULL - field is not nullable")
        
        # Set foreign key to NULL for related objects
        related_objects = self._get_related_objects(instance, config)
        for obj in related_objects:
            setattr(obj, config.foreign_key_field, None)
    
    def _handle_set_default(self, instance, config: RelationshipConfig):
        """Handle SET_DEFAULT cascade action"""
        # Set foreign key to default value for related objects
        related_objects = self._get_related_objects(instance, config)
        default_value = self._get_field_default(config.target_model, config.foreign_key_field)
        for obj in related_objects:
            setattr(obj, config.foreign_key_field, default_value)
    
    def _handle_no_action(self, instance, config: RelationshipConfig):
        """Handle NO_ACTION cascade action"""
        # Do nothing
        pass
    
    def _get_related_objects(self, instance, config: RelationshipConfig) -> List[Any]:
        """Get related objects for an instance"""
        # This would integrate with the database layer
        return []
    
    def _get_field_default(self, model_class: Type, field_name: str) -> Any:
        """Get default value for a field"""
        # This would get the default from the Pydantic field definition
        return None


# =============================================================================
# RELATIONSHIP DEFINITIONS
# =============================================================================

class ModelRelationships:
    """Define all relationships between models"""
    
    @staticmethod
    def get_core_relationships() -> List[RelationshipConfig]:
        """Get core model relationships"""
        from .core_models import (
            Platform, Content, ContentMetadata, Download, 
            DownloadSession, DownloadError, QualityOption,
            Tag, ContentTag
        )
        
        return [
            # Platform -> Content (One-to-Many)
            RelationshipConfig(
                name="platform_content",
                source_model=Platform,
                target_model=Content,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="platform_id",
                on_delete=CascadeAction.RESTRICT,
                back_reference="platform"
            ),
            
            # Content -> ContentMetadata (One-to-Many)
            RelationshipConfig(
                name="content_metadata",
                source_model=Content,
                target_model=ContentMetadata,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="content_id",
                on_delete=CascadeAction.CASCADE,
                back_reference="content"
            ),
            
            # Content -> Download (One-to-Many)
            RelationshipConfig(
                name="content_downloads",
                source_model=Content,
                target_model=Download,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="content_id",
                on_delete=CascadeAction.CASCADE,
                back_reference="content"
            ),
            
            # Content -> QualityOption (One-to-Many)
            RelationshipConfig(
                name="content_quality_options",
                source_model=Content,
                target_model=QualityOption,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="content_id",
                on_delete=CascadeAction.CASCADE,
                back_reference="content"
            ),
            
            # Download -> DownloadSession (One-to-Many)
            RelationshipConfig(
                name="download_sessions",
                source_model=Download,
                target_model=DownloadSession,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="download_id",
                on_delete=CascadeAction.CASCADE,
                back_reference="download"
            ),
            
            # Download -> DownloadError (One-to-Many)
            RelationshipConfig(
                name="download_errors",
                source_model=Download,
                target_model=DownloadError,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="download_id",
                on_delete=CascadeAction.CASCADE,
                back_reference="download"
            ),
            
            # DownloadSession -> DownloadError (One-to-Many)
            RelationshipConfig(
                name="session_errors",
                source_model=DownloadSession,
                target_model=DownloadError,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="session_id",
                on_delete=CascadeAction.SET_NULL,
                nullable=True,
                back_reference="session"
            ),
            
            # Content <-> Tag (Many-to-Many through ContentTag)
            RelationshipConfig(
                name="content_tags_content",
                source_model=Content,
                target_model=ContentTag,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="content_id",
                on_delete=CascadeAction.CASCADE,
                back_reference="content"
            ),
            
            RelationshipConfig(
                name="content_tags_tag",
                source_model=Tag,
                target_model=ContentTag,
                relationship_type=RelationshipType.ONE_TO_MANY,
                foreign_key_field="tag_id",
                on_delete=CascadeAction.CASCADE,
                back_reference="tag"
            ),
        ]


# =============================================================================
# RELATIONSHIP MIXIN
# =============================================================================

class RelationshipMixin:
    """Mixin to add relationship functionality to models"""
    
    _relationship_manager: Optional[RelationshipManager] = None
    
    @classmethod
    def set_relationship_manager(cls, manager: RelationshipManager):
        """Set the relationship manager for all models"""
        cls._relationship_manager = manager
    
    def get_related(self, relationship_name: str):
        """Get related objects for a named relationship"""
        if not self._relationship_manager:
            raise ValueError("No relationship manager configured")
        
        config = self._relationship_manager.get_relationship(relationship_name)
        if not config:
            raise ValueError(f"Unknown relationship: {relationship_name}")
        
        descriptor = RelationshipDescriptor(config)
        return descriptor.__get__(self, type(self))
    
    def set_related(self, relationship_name: str, value):
        """Set related objects for a named relationship"""
        if not self._relationship_manager:
            raise ValueError("No relationship manager configured")
        
        config = self._relationship_manager.get_relationship(relationship_name)
        if not config:
            raise ValueError(f"Unknown relationship: {relationship_name}")
        
        descriptor = RelationshipDescriptor(config)
        descriptor.__set__(self, value)
    
    def validate_relationships(self) -> List[str]:
        """Validate all relationships for this instance"""
        if not self._relationship_manager:
            return []
        
        return self._relationship_manager.validate_referential_integrity(self)
    
    def delete_with_cascade(self):
        """Delete this instance with cascade operations"""
        if not self._relationship_manager:
            raise ValueError("No relationship manager configured")
        
        # Validate referential integrity first
        errors = self.validate_relationships()
        if errors:
            raise ValueError(f"Cannot delete: {'; '.join(errors)}")
        
        # Execute cascade operations
        self._relationship_manager.execute_cascade_operations(self, 'delete')


# =============================================================================
# RELATIONSHIP QUERY HELPERS
# =============================================================================

class RelationshipQueryBuilder:
    """Helper for building queries with relationships"""
    
    def __init__(self, model_class: Type):
        self.model_class = model_class
        self.joins = []
        self.where_conditions = []
    
    def join(self, relationship_name: str, alias: Optional[str] = None):
        """Add a join for a relationship"""
        self.joins.append({
            'relationship': relationship_name,
            'alias': alias
        })
        return self
    
    def where(self, condition: str):
        """Add a where condition"""
        self.where_conditions.append(condition)
        return self
    
    def build_query(self) -> str:
        """Build the SQL query (placeholder)"""
        # This would build actual SQL query
        return f"SELECT * FROM {self.model_class._table_name}"


# =============================================================================
# RELATIONSHIP UTILITIES
# =============================================================================

def setup_model_relationships(manager: RelationshipManager):
    """Set up all model relationships"""
    # Register core relationships
    for config in ModelRelationships.get_core_relationships():
        manager.register_relationship(config)
    
    logger.info(f"Registered {len(manager.relationships)} relationships")


def get_relationship_graph() -> Dict[str, List[str]]:
    """Get a graph representation of all relationships"""
    manager = RelationshipManager()
    setup_model_relationships(manager)
    
    graph = {}
    for config in manager.relationships.values():
        source_name = config.source_model.__name__
        target_name = config.target_model.__name__
        
        if source_name not in graph:
            graph[source_name] = []
        graph[source_name].append(target_name)
    
    return graph


def validate_relationship_integrity(instances: List[Any]) -> Dict[str, List[str]]:
    """Validate relationship integrity across multiple instances"""
    errors = {}
    manager = RelationshipManager()
    setup_model_relationships(manager)
    
    for instance in instances:
        instance_errors = manager.validate_referential_integrity(instance)
        if instance_errors:
            instance_key = f"{type(instance).__name__}_{getattr(instance, 'id', 'unknown')}"
            errors[instance_key] = instance_errors
    
    return errors


# =============================================================================
# GLOBAL RELATIONSHIP MANAGER INSTANCE
# =============================================================================

# Global instance for easy access
_global_relationship_manager = RelationshipManager()
setup_model_relationships(_global_relationship_manager)

def get_relationship_manager() -> RelationshipManager:
    """Get the global relationship manager"""
    return _global_relationship_manager 