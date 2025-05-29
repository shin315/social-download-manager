"""
Pydantic Data Models for Social Download Manager v2.0

Modern typed data models using Pydantic for enhanced type safety,
validation, and serialization capabilities.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, ClassVar
from uuid import UUID, uuid4

from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
    field_validator,
    model_validator,
    computed_field,
    field_serializer
)
from pydantic.types import PositiveInt, NonNegativeInt


# =============================================================================
# TYPE ALIASES & ENUMS
# =============================================================================

EntityId = Union[int, str]
JsonData = Dict[str, Any]


class ContentType(str, Enum):
    """Valid content types"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image" 
    POST = "post"
    STORY = "story"
    REEL = "reel"
    LIVESTREAM = "livestream"
    PLAYLIST = "playlist"


class ContentStatus(str, Enum):
    """Valid content status values"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class DownloadStatus(str, Enum):
    """Valid download status values"""
    QUEUED = "queued"
    STARTING = "starting"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


class SessionType(str, Enum):
    """Download session types"""
    STANDARD = "standard"
    RETRY = "retry"
    RESUME = "resume"
    PARALLEL = "parallel"


class SessionStatus(str, Enum):
    """Download session status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TagType(str, Enum):
    """Tag classification types"""
    USER = "user"
    AUTO = "auto"
    HASHTAG = "hashtag"
    CATEGORY = "category"
    SYSTEM = "system"


class DataType(str, Enum):
    """Metadata data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    TIMESTAMP = "timestamp"


# =============================================================================
# BASE MODEL CLASSES
# =============================================================================

class SDMBaseModel(BaseModel):
    """
    Base Pydantic model for all Social Download Manager entities.
    
    Provides common functionality, validation, and serialization for all models.
    """
    
    model_config = ConfigDict(
        # Validation settings
        validate_assignment=True,
        validate_default=True,
        extra='forbid',
        
        # Serialization settings
        str_strip_whitespace=True,
        use_enum_values=True,
        
        # JSON settings
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
            Path: lambda v: str(v),
            UUID: lambda v: str(v)
        },
        
        # Performance
        arbitrary_types_allowed=True,
        frozen=False  # Allow updates for database operations
    )
    
    @field_serializer('*', when_used='json')
    def serialize_special_types(self, value: Any) -> Any:
        """Custom serialization for special types"""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, (Path, UUID)):
            return str(value)
        return value
    
    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert model to dictionary with proper type conversion"""
        return self.model_dump(
            exclude_none=exclude_none,
            by_alias=True,
            mode='python'
        )
    
    def to_json(self, exclude_none: bool = True) -> str:
        """Convert model to JSON string"""
        return self.model_dump_json(
            exclude_none=exclude_none,
            by_alias=True
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SDMBaseModel':
        """Create model instance from dictionary"""
        return cls.model_validate(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SDMBaseModel':
        """Create model instance from JSON string"""
        return cls.model_validate_json(json_str)
    
    @classmethod 
    def from_db_row(cls, row_data: Dict[str, Any]) -> 'SDMBaseModel':
        """
        Create model instance from database row data.
        Handles type conversion from SQLite types.
        """
        # Make a copy to avoid modifying original
        data = dict(row_data)
        
        # Convert timestamp strings to datetime objects
        for field_name, field_info in cls.model_fields.items():
            if field_name in data and data[field_name] is not None:
                if field_info.annotation == datetime or \
                   getattr(field_info.annotation, '__origin__', None) is Union and \
                   datetime in getattr(field_info.annotation, '__args__', []):
                    
                    value = data[field_name]
                    if isinstance(value, str):
                        try:
                            # Handle various timestamp formats
                            if 'T' in value:
                                data[field_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            else:
                                data[field_name] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            logging.warning(f"Could not parse timestamp {value} for field {field_name}")
                            data[field_name] = None
        
        return cls.model_validate(data)


class TimestampedModel(SDMBaseModel):
    """
    Base model with automatic timestamp management.
    
    Provides created_at and updated_at fields with automatic updates.
    """
    
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the entity was created"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the entity was last updated"
    )
    
    def mark_updated(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)


class VersionedModel(TimestampedModel):
    """
    Model with version tracking for optimistic locking.
    """
    
    version: PositiveInt = Field(
        default=1,
        description="Version number for optimistic locking"
    )
    
    def increment_version(self) -> None:
        """Increment version and update timestamp"""
        self.version += 1
        self.mark_updated()


class SoftDeletableModel(VersionedModel):
    """
    Model with soft delete capability.
    """
    
    is_deleted: bool = Field(
        default=False,
        description="Whether the entity is soft deleted"
    )
    
    def soft_delete(self) -> None:
        """Mark entity as soft deleted"""
        self.is_deleted = True
        self.increment_version()
    
    def restore(self) -> None:
        """Restore soft deleted entity"""
        self.is_deleted = False
        self.increment_version()


class DatabaseEntity(SoftDeletableModel):
    """
    Complete base model for database entities.
    
    Combines all common functionality needed for database-backed entities.
    """
    
    id: Optional[PositiveInt] = Field(
        default=None,
        description="Primary key identifier"
    )
    
    # Abstract table name - must be set by subclasses
    _table_name: ClassVar[str] = ""
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get the database table name for this model"""
        if not cls._table_name:
            raise NotImplementedError(f"Table name not defined for {cls.__name__}")
        return cls._table_name
    
    @model_validator(mode='after')
    def validate_entity(self):
        """Custom validation logic - can be overridden by subclasses"""
        return self
    
    def is_persisted(self) -> bool:
        """Check if entity has been saved to database"""
        return self.id is not None
    
    def is_new(self) -> bool:
        """Check if entity is new (not persisted)"""
        return self.id is None


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_url(value: str) -> str:
    """Validate URL format"""
    if not value or not value.strip():
        raise ValueError("URL cannot be empty")
    
    value = value.strip()
    if not (value.startswith('http://') or value.startswith('https://')):
        raise ValueError("URL must start with http:// or https://")
    
    return value


def validate_json_string(value: str) -> str:
    """Validate JSON string format"""
    if not value:
        return "{}"
    
    try:
        json.loads(value)
        return value
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format")


def validate_positive_numeric(value: Union[int, float, Decimal]) -> Union[int, float, Decimal]:
    """Validate positive numeric values"""
    if value is not None and value < 0:
        raise ValueError("Value must be positive")
    return value


def validate_percentage(value: float) -> float:
    """Validate percentage values (0-100)"""
    if value is not None and (value < 0 or value > 100):
        raise ValueError("Percentage must be between 0 and 100")
    return value


def validate_slug(value: str) -> str:
    """Validate slug format (lowercase, no spaces)"""
    if not value:
        raise ValueError("Slug cannot be empty")
    
    value = value.strip().lower()
    if ' ' in value:
        raise ValueError("Slug cannot contain spaces")
    
    return value 