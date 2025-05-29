"""
Serialization Integration for Social Download Manager v2.0

Integration layer that enhances existing models with comprehensive
serialization capabilities, providing seamless conversion between
models and various data formats.
"""

from typing import Any, Dict, List, Optional, Type, Union, ClassVar
from pathlib import Path
import json
import logging

from .pydantic_models import DatabaseEntity, SDMBaseModel
from .core_models import (
    Platform, Content, ContentMetadata, Download,
    DownloadSession, DownloadError, QualityOption,
    Tag, ContentTag, ApplicationSetting
)
from .platform_models import (
    TikTokContent, YouTubeContent, InstagramContent,
    TikTokMetadata, YouTubeMetadata, InstagramMetadata
)
from .serializers import (
    JSONSerializer, DatabaseSerializer, SerializerFactory,
    SerializationFormat, ModelExporter, ModelImporter,
    SchemaGenerator, BulkSerializer, CustomJSONEncoder,
    CustomJSONDecoder, Serializable, DatabaseSerializable
)

logger = logging.getLogger(__name__)


# =============================================================================
# SERIALIZATION MIXIN
# =============================================================================

class SerializationMixin(Serializable, DatabaseSerializable):
    """Mixin to add serialization capabilities to models"""
    
    _serializers: ClassVar[Dict[SerializationFormat, Any]] = {}
    _table_name: ClassVar[str] = ""
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Auto-register serializers for the model class
        cls._setup_serializers()
    
    @classmethod
    def _setup_serializers(cls):
        """Set up serializers for this model class"""
        # JSON serializer
        cls._serializers[SerializationFormat.JSON] = JSONSerializer(
            cls, 
            include_type_info=True,
            pretty_print=False
        )
        
        # Database serializer
        table_name = getattr(cls, '_table_name', cls.__name__.lower())
        cls._serializers[SerializationFormat.DATABASE] = DatabaseSerializer(
            cls,
            table_name=table_name
        )
    
    # Serializable Protocol Implementation
    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(**kwargs)
    
    def to_json(self, pretty: bool = False, **kwargs) -> str:
        """Convert to JSON string"""
        serializer = self._get_serializer(SerializationFormat.JSON)
        if pretty:
            serializer.pretty_print = True
        try:
            return serializer.serialize(self, **kwargs)
        finally:
            if pretty:
                serializer.pretty_print = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], **kwargs):
        """Create instance from dictionary"""
        return cls.model_validate(data)
    
    @classmethod
    def from_json(cls, json_str: str, **kwargs):
        """Create instance from JSON string"""
        serializer = cls._get_serializer(SerializationFormat.JSON)
        return serializer.deserialize(json_str, **kwargs)
    
    # DatabaseSerializable Protocol Implementation
    def to_db_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to database-compatible dictionary"""
        serializer = self._get_serializer(SerializationFormat.DATABASE)
        return serializer.serialize(self, **kwargs)
    
    @classmethod
    def from_db_dict(cls, data: Dict[str, Any], **kwargs):
        """Create instance from database dictionary"""
        serializer = cls._get_serializer(SerializationFormat.DATABASE)
        return serializer.deserialize(data, **kwargs)
    
    # Extended Serialization Methods
    def to_format(self, format_type: SerializationFormat, **kwargs) -> Any:
        """Convert to specified format"""
        serializer = self._get_serializer(format_type)
        return serializer.serialize(self, **kwargs)
    
    @classmethod
    def from_format(cls, data: Any, format_type: SerializationFormat, **kwargs):
        """Create instance from specified format"""
        serializer = cls._get_serializer(format_type)
        return serializer.deserialize(data, **kwargs)
    
    def export_to_file(self, file_path: Path, 
                      format_type: SerializationFormat = SerializationFormat.JSON,
                      **kwargs) -> bool:
        """Export instance to file"""
        try:
            exporter = ModelExporter(self.__class__)
            return exporter.export_to_file([self], file_path, format_type, **kwargs)
        except Exception as e:
            logger.error(f"Failed to export {self.__class__.__name__} to {file_path}: {str(e)}")
            return False
    
    @classmethod
    def import_from_file(cls, file_path: Path,
                        format_type: SerializationFormat = SerializationFormat.JSON,
                        **kwargs) -> List[Optional['SerializationMixin']]:
        """Import instances from file"""
        try:
            importer = ModelImporter(cls)
            return importer.import_from_file(file_path, format_type, **kwargs)
        except Exception as e:
            logger.error(f"Failed to import {cls.__name__} from {file_path}: {str(e)}")
            return []
    
    @classmethod
    def generate_schema(cls, format_type: str = 'json', 
                       include_examples: bool = True) -> Dict[str, Any]:
        """Generate schema for this model"""
        if format_type.lower() == 'json':
            return SchemaGenerator.generate_json_schema(cls, include_examples)
        elif format_type.lower() == 'database':
            return SchemaGenerator.generate_database_schema(cls)
        else:
            raise ValueError(f"Unsupported schema format: {format_type}")
    
    @classmethod
    def _get_serializer(cls, format_type: SerializationFormat):
        """Get serializer for format type"""
        if format_type not in cls._serializers:
            cls._setup_serializers()
        
        if format_type not in cls._serializers:
            raise ValueError(f"No serializer available for format: {format_type}")
        
        return cls._serializers[format_type]
    
    # Comparison and Validation
    def equals_serialized(self, other: 'SerializationMixin', 
                         format_type: SerializationFormat = SerializationFormat.JSON) -> bool:
        """Check if two instances are equal when serialized"""
        if not isinstance(other, self.__class__):
            return False
        
        try:
            self_data = self.to_format(format_type)
            other_data = other.to_format(format_type)
            return self_data == other_data
        except Exception:
            return False
    
    def validate_serialization_roundtrip(self, 
                                       format_type: SerializationFormat = SerializationFormat.JSON) -> bool:
        """Validate that serialization->deserialization preserves data"""
        try:
            serialized = self.to_format(format_type)
            deserialized = self.__class__.from_format(serialized, format_type)
            return self.equals_serialized(deserialized, format_type)
        except Exception as e:
            logger.warning(f"Serialization roundtrip validation failed: {str(e)}")
            return False


# =============================================================================
# ENHANCED MODEL CLASSES
# =============================================================================

class SerializablePlatform(Platform, SerializationMixin):
    """Platform model with serialization capabilities"""
    _table_name: ClassVar[str] = "platforms"
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'base_url': self.base_url,
            'is_active': self.is_active,
            'supported_content_types': json.loads(self.supported_content_types) if self.supported_content_types else []
        }
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'SerializablePlatform':
        """Create instance from API response data"""
        # Handle supported_content_types conversion
        if 'supported_content_types' in data and isinstance(data['supported_content_types'], list):
            data['supported_content_types'] = json.dumps(data['supported_content_types'])
        
        return cls.model_validate(data)


class SerializableContent(Content, SerializationMixin):
    """Content model with serialization capabilities"""
    _table_name: ClassVar[str] = "content"
    
    def to_api_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Convert to API-friendly dictionary"""
        data = {
            'id': self.id,
            'platform_id': self.platform_id,
            'platform_content_id': self.platform_content_id,
            'content_type': self.content_type,
            'title': self.title,
            'description': self.description,
            'author_username': self.author_username,
            'content_url': self.content_url,
            'thumbnail_url': self.thumbnail_url,
            'duration_seconds': self.duration_seconds,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None
        }
        
        # Include computed properties
        data.update({
            'engagement_total': self.engagement_total,
            'is_downloadable': self.is_downloadable,
            'has_audio': self.has_audio,
            'has_video': self.has_video
        })
        
        return data
    
    def to_download_request(self) -> Dict[str, Any]:
        """Convert to download request format"""
        return {
            'content_id': self.id,
            'content_url': self.content_url,
            'title': self.title,
            'author': self.author_username,
            'duration': self.duration_seconds,
            'content_type': self.content_type,
            'platform': self.platform_id
        }


class SerializableDownload(Download, SerializationMixin):
    """Download model with serialization capabilities"""
    _table_name: ClassVar[str] = "downloads"
    
    def to_status_dict(self) -> Dict[str, Any]:
        """Convert to status dictionary for monitoring"""
        return {
            'id': self.id,
            'content_id': self.content_id,
            'status': self.status,
            'progress_percentage': float(self.progress_percentage) if self.progress_percentage else 0,
            'current_speed_bps': self.current_speed_bps,
            'average_speed_bps': self.average_speed_bps,
            'retry_count': self.retry_count,
            'error_count': self.error_count,
            'can_retry': self.can_retry,
            'estimated_time_remaining': self.estimated_time_remaining,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_error_message': self.last_error_message
        }
    
    def to_progress_update(self) -> Dict[str, Any]:
        """Convert to progress update format for real-time updates"""
        return {
            'download_id': self.id,
            'progress': float(self.progress_percentage) if self.progress_percentage else 0,
            'speed': self.current_speed_bps,
            'status': self.status,
            'eta': self.estimated_time_remaining,
            'timestamp': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# PLATFORM-SPECIFIC SERIALIZABLE MODELS
# =============================================================================

class SerializableTikTokContent(TikTokContent, SerializationMixin):
    """TikTok content with serialization capabilities"""
    _table_name: ClassVar[str] = "content"
    
    def to_tiktok_api_dict(self) -> Dict[str, Any]:
        """Convert to TikTok API format"""
        base_data = self.to_api_dict()
        
        # Add TikTok-specific fields
        tiktok_data = {
            'video_type': self.video_type,
            'music_title': self.music_title,
            'music_author': self.music_author,
            'effects_used': self.effects_used,
            'hashtags': self.hashtags,
            'is_duet': self.is_duet,
            'is_stitch': self.is_stitch,
            'original_video_id': self.original_video_id,
            'is_duet_or_stitch': self.is_duet_or_stitch,
            'total_tiktok_engagement': self.total_tiktok_engagement
        }
        
        base_data.update(tiktok_data)
        return base_data


class SerializableYouTubeContent(YouTubeContent, SerializationMixin):
    """YouTube content with serialization capabilities"""
    _table_name: ClassVar[str] = "content"
    
    def to_youtube_api_dict(self) -> Dict[str, Any]:
        """Convert to YouTube API format"""
        base_data = self.to_api_dict()
        
        # Add YouTube-specific fields
        youtube_data = {
            'video_type': self.video_type,
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'category_id': self.category_id,
            'has_captions': self.has_captions,
            'caption_languages': self.caption_languages,
            'privacy_status': self.privacy_status,
            'live_broadcast_content': self.live_broadcast_content,
            'is_live_content': self.is_live_content,
            'is_short_form': self.is_short_form
        }
        
        base_data.update(youtube_data)
        return base_data


class SerializableInstagramContent(InstagramContent, SerializationMixin):
    """Instagram content with serialization capabilities"""
    _table_name: ClassVar[str] = "content"
    
    def to_instagram_api_dict(self) -> Dict[str, Any]:
        """Convert to Instagram API format"""
        base_data = self.to_api_dict()
        
        # Add Instagram-specific fields
        instagram_data = {
            'media_type': self.media_type,
            'carousel_media_count': self.carousel_media_count,
            'location_id': self.location_id,
            'location_name': self.location_name,
            'is_story': self.is_story,
            'story_expires_at': self.story_expires_at.isoformat() if self.story_expires_at else None,
            'is_carousel': self.is_carousel,
            'is_temporary_content': self.is_temporary_content
        }
        
        base_data.update(instagram_data)
        return base_data


# =============================================================================
# BULK OPERATIONS WITH SERIALIZATION
# =============================================================================

class BulkSerializationOperations:
    """Handle bulk serialization operations for models"""
    
    @staticmethod
    def export_models_to_json(models: List[SerializationMixin], 
                            file_path: Path,
                            pretty_print: bool = True) -> bool:
        """Export multiple models to JSON file"""
        try:
            data = []
            for model in models:
                model_data = {
                    '__model_class__': f"{model.__class__.__module__}.{model.__class__.__name__}",
                    '__data__': model.to_dict()
                }
                data.append(model_data)
            
            with file_path.open('w', encoding='utf-8') as f:
                if pretty_print:
                    json.dump(data, f, cls=CustomJSONEncoder, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, cls=CustomJSONEncoder, ensure_ascii=False)
            
            logger.info(f"Exported {len(models)} models to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export models to {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def import_models_from_json(file_path: Path) -> List[Optional[SerializationMixin]]:
        """Import multiple models from JSON file"""
        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f, object_hook=CustomJSONDecoder.object_hook)
            
            models = []
            for item in data:
                if isinstance(item, dict) and '__model_class__' in item:
                    class_path = item['__model_class__']
                    model_data = item['__data__']
                    
                    try:
                        # Import the model class
                        module_name, class_name = class_path.rsplit('.', 1)
                        module = __import__(module_name, fromlist=[class_name])
                        model_class = getattr(module, class_name)
                        
                        # Create instance
                        instance = model_class.from_dict(model_data)
                        models.append(instance)
                        
                    except (ImportError, AttributeError, ValueError) as e:
                        logger.warning(f"Could not import model {class_path}: {e}")
                        models.append(None)
                else:
                    models.append(None)
            
            logger.info(f"Imported {len([m for m in models if m])} models from {file_path}")
            return models
            
        except Exception as e:
            logger.error(f"Failed to import models from {file_path}: {str(e)}")
            return []
    
    @staticmethod
    def convert_models_format(models: List[SerializationMixin],
                            from_format: SerializationFormat,
                            to_format: SerializationFormat) -> List[Dict[str, Any]]:
        """Convert models between formats"""
        results = []
        
        for model in models:
            try:
                # Serialize to intermediate format
                intermediate = model.to_format(from_format)
                
                # Deserialize and re-serialize to target format
                temp_instance = model.__class__.from_format(intermediate, from_format)
                target_data = temp_instance.to_format(to_format)
                
                results.append(target_data)
                
            except Exception as e:
                logger.error(f"Failed to convert model format: {str(e)}")
                results.append(None)
        
        return results


# =============================================================================
# REGISTRY AND FACTORY
# =============================================================================

class SerializableModelRegistry:
    """Registry for serializable model classes"""
    
    _models: Dict[str, Type[SerializationMixin]] = {}
    
    @classmethod
    def register(cls, model_class: Type[SerializationMixin], name: Optional[str] = None):
        """Register a serializable model class"""
        name = name or model_class.__name__
        cls._models[name] = model_class
        logger.debug(f"Registered serializable model: {name}")
    
    @classmethod
    def get_model(cls, name: str) -> Optional[Type[SerializationMixin]]:
        """Get model class by name"""
        return cls._models.get(name)
    
    @classmethod
    def list_models(cls) -> List[str]:
        """List all registered model names"""
        return list(cls._models.keys())
    
    @classmethod
    def create_instance(cls, model_name: str, data: Dict[str, Any]) -> Optional[SerializationMixin]:
        """Create model instance by name"""
        model_class = cls.get_model(model_name)
        if model_class:
            try:
                return model_class.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to create {model_name} instance: {str(e)}")
        return None


# Register core serializable models
SerializableModelRegistry.register(SerializablePlatform, 'Platform')
SerializableModelRegistry.register(SerializableContent, 'Content')
SerializableModelRegistry.register(SerializableDownload, 'Download')
SerializableModelRegistry.register(SerializableTikTokContent, 'TikTokContent')
SerializableModelRegistry.register(SerializableYouTubeContent, 'YouTubeContent')
SerializableModelRegistry.register(SerializableInstagramContent, 'InstagramContent')


# =============================================================================
# UTILITIES
# =============================================================================

def validate_model_serialization(model: SerializationMixin) -> Dict[str, Any]:
    """Validate serialization capabilities of a model"""
    results = {
        'model_class': model.__class__.__name__,
        'json_serialization': False,
        'database_serialization': False,
        'roundtrip_json': False,
        'roundtrip_database': False,
        'errors': []
    }
    
    try:
        # Test JSON serialization
        json_data = model.to_json()
        model.__class__.from_json(json_data)
        results['json_serialization'] = True
        
        # Test JSON roundtrip
        results['roundtrip_json'] = model.validate_serialization_roundtrip(SerializationFormat.JSON)
        
    except Exception as e:
        results['errors'].append(f"JSON serialization error: {str(e)}")
    
    try:
        # Test database serialization
        db_data = model.to_db_dict()
        model.__class__.from_db_dict(db_data)
        results['database_serialization'] = True
        
        # Test database roundtrip
        results['roundtrip_database'] = model.validate_serialization_roundtrip(SerializationFormat.DATABASE)
        
    except Exception as e:
        results['errors'].append(f"Database serialization error: {str(e)}")
    
    return results


def generate_all_schemas() -> Dict[str, Dict[str, Any]]:
    """Generate schemas for all registered models"""
    schemas = {}
    
    for model_name in SerializableModelRegistry.list_models():
        model_class = SerializableModelRegistry.get_model(model_name)
        if model_class:
            try:
                schemas[model_name] = {
                    'json_schema': model_class.generate_schema('json'),
                    'database_schema': model_class.generate_schema('database')
                }
            except Exception as e:
                logger.error(f"Failed to generate schema for {model_name}: {str(e)}")
                schemas[model_name] = {'error': str(e)}
    
    return schemas 