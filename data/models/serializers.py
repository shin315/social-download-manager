"""
Serialization and Deserialization System for Social Download Manager v2.0

Comprehensive system for converting models to and from various formats
including JSON, dictionaries, database records, and other data formats.
Supports custom encoders/decoders and schema generation.
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone, date, time
from decimal import Decimal
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Type, TypeVar, Generic,
    Callable, Protocol, runtime_checkable
)
from enum import Enum
import logging

from pydantic import BaseModel
from pydantic._internal._model_serialization import to_jsonable_python

logger = logging.getLogger(__name__)

# Type aliases
ModelType = TypeVar('ModelType', bound=BaseModel)
SerializableType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


# =============================================================================
# CUSTOM ENCODERS AND DECODERS
# =============================================================================

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling special types"""
    
    def default(self, obj):
        """Convert special types to JSON-serializable formats"""
        if isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                'value': obj.isoformat()
            }
        elif isinstance(obj, date):
            return {
                '__type__': 'date', 
                'value': obj.isoformat()
            }
        elif isinstance(obj, time):
            return {
                '__type__': 'time',
                'value': obj.isoformat()
            }
        elif isinstance(obj, Decimal):
            return {
                '__type__': 'decimal',
                'value': str(obj)
            }
        elif isinstance(obj, Path):
            return {
                '__type__': 'path',
                'value': str(obj)
            }
        elif isinstance(obj, uuid.UUID):
            return {
                '__type__': 'uuid',
                'value': str(obj)
            }
        elif isinstance(obj, Enum):
            return {
                '__type__': 'enum',
                'class': f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                'value': obj.value
            }
        elif isinstance(obj, BaseModel):
            return {
                '__type__': 'pydantic_model',
                'class': f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                'data': obj.model_dump()
            }
        elif hasattr(obj, '__dict__'):
            # Generic object with __dict__
            return {
                '__type__': 'object',
                'class': f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                'data': obj.__dict__
            }
        
        return super().default(obj)


class CustomJSONDecoder:
    """Custom JSON decoder for reconstructing special types"""
    
    @staticmethod
    def object_hook(obj: Dict[str, Any]) -> Any:
        """Reconstruct objects from JSON representation"""
        if '__type__' not in obj:
            return obj
        
        obj_type = obj['__type__']
        value = obj.get('value')
        
        if obj_type == 'datetime':
            return datetime.fromisoformat(value)
        elif obj_type == 'date':
            return date.fromisoformat(value)
        elif obj_type == 'time':
            return time.fromisoformat(value)
        elif obj_type == 'decimal':
            return Decimal(value)
        elif obj_type == 'path':
            return Path(value)
        elif obj_type == 'uuid':
            return uuid.UUID(value)
        elif obj_type == 'enum':
            # Reconstruct enum (requires import)
            class_path = obj['class']
            try:
                module_name, class_name = class_path.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                enum_class = getattr(module, class_name)
                return enum_class(value)
            except (ImportError, AttributeError, ValueError) as e:
                logger.warning(f"Could not reconstruct enum {class_path}: {e}")
                return value
        elif obj_type == 'pydantic_model':
            # Reconstruct Pydantic model
            class_path = obj['class']
            try:
                module_name, class_name = class_path.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                model_class = getattr(module, class_name)
                return model_class.model_validate(obj['data'])
            except (ImportError, AttributeError, ValueError) as e:
                logger.warning(f"Could not reconstruct model {class_path}: {e}")
                return obj['data']
        elif obj_type == 'object':
            # Generic object reconstruction (limited)
            return obj['data']
        
        return obj


# =============================================================================
# SERIALIZATION PROTOCOLS
# =============================================================================

@runtime_checkable
class Serializable(Protocol):
    """Protocol for serializable objects"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        ...
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create instance from dictionary"""
        ...
    
    @classmethod 
    def from_json(cls, json_str: str):
        """Create instance from JSON string"""
        ...


@runtime_checkable
class DatabaseSerializable(Protocol):
    """Protocol for database serialization"""
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database-compatible dictionary"""
        ...
    
    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]):
        """Create instance from database dictionary"""
        ...


# =============================================================================
# SERIALIZATION FORMATS
# =============================================================================

class SerializationFormat(str, Enum):
    """Supported serialization formats"""
    JSON = "json"
    DICT = "dict"
    DATABASE = "database"
    XML = "xml"
    YAML = "yaml"
    CSV = "csv"
    MSGPACK = "msgpack"


# =============================================================================
# BASE SERIALIZER
# =============================================================================

class BaseSerializer(ABC, Generic[ModelType]):
    """Base class for model serializers"""
    
    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class
        self.custom_encoders: Dict[Type, Callable] = {}
        self.custom_decoders: Dict[Type, Callable] = {}
    
    def register_encoder(self, type_class: Type, encoder: Callable):
        """Register custom encoder for a type"""
        self.custom_encoders[type_class] = encoder
    
    def register_decoder(self, type_class: Type, decoder: Callable):
        """Register custom decoder for a type"""
        self.custom_decoders[type_class] = decoder
    
    @abstractmethod
    def serialize(self, instance: ModelType, **kwargs) -> Any:
        """Serialize model instance"""
        pass
    
    @abstractmethod
    def deserialize(self, data: Any, **kwargs) -> ModelType:
        """Deserialize data to model instance"""
        pass
    
    def _apply_custom_encoders(self, obj: Any) -> Any:
        """Apply custom encoders to object"""
        obj_type = type(obj)
        if obj_type in self.custom_encoders:
            return self.custom_encoders[obj_type](obj)
        return obj
    
    def _apply_custom_decoders(self, obj: Any, target_type: Type) -> Any:
        """Apply custom decoders to object"""
        if target_type in self.custom_decoders:
            return self.custom_decoders[target_type](obj)
        return obj


# =============================================================================
# JSON SERIALIZER
# =============================================================================

class JSONSerializer(BaseSerializer[ModelType]):
    """JSON serialization for Pydantic models"""
    
    def __init__(self, model_class: Type[ModelType], 
                 include_type_info: bool = True,
                 pretty_print: bool = False):
        super().__init__(model_class)
        self.include_type_info = include_type_info
        self.pretty_print = pretty_print
    
    def serialize(self, instance: ModelType, **kwargs) -> str:
        """Serialize model to JSON string"""
        try:
            # Get model data
            data = instance.model_dump(**kwargs)
            
            # Add type information if requested
            if self.include_type_info:
                data['__model_class__'] = f"{instance.__class__.__module__}.{instance.__class__.__name__}"
                data['__serialized_at__'] = datetime.now(timezone.utc).isoformat()
            
            # Apply custom encoders
            data = self._apply_custom_transforms(data, 'encode')
            
            # Serialize to JSON
            if self.pretty_print:
                return json.dumps(data, cls=CustomJSONEncoder, indent=2, ensure_ascii=False)
            else:
                return json.dumps(data, cls=CustomJSONEncoder, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to serialize {self.model_class.__name__} to JSON: {str(e)}")
            raise
    
    def deserialize(self, json_str: str, **kwargs) -> ModelType:
        """Deserialize JSON string to model"""
        try:
            # Parse JSON with custom decoder
            data = json.loads(json_str, object_hook=CustomJSONDecoder.object_hook)
            
            # Remove type information if present
            if isinstance(data, dict):
                data.pop('__model_class__', None)
                data.pop('__serialized_at__', None)
            
            # Apply custom decoders
            data = self._apply_custom_transforms(data, 'decode')
            
            # Create model instance
            return self.model_class.model_validate(data)
            
        except Exception as e:
            logger.error(f"Failed to deserialize JSON to {self.model_class.__name__}: {str(e)}")
            raise
    
    def _apply_custom_transforms(self, obj: Any, operation: str) -> Any:
        """Apply custom transformations recursively"""
        if isinstance(obj, dict):
            return {k: self._apply_custom_transforms(v, operation) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._apply_custom_transforms(item, operation) for item in obj]
        else:
            if operation == 'encode':
                return self._apply_custom_encoders(obj)
            else:
                return obj  # Decoders are applied in object_hook


# =============================================================================
# DATABASE SERIALIZER
# =============================================================================

class DatabaseSerializer(BaseSerializer[ModelType]):
    """Database serialization for Pydantic models"""
    
    def __init__(self, model_class: Type[ModelType],
                 table_name: Optional[str] = None,
                 field_mappings: Optional[Dict[str, str]] = None):
        super().__init__(model_class)
        self.table_name = table_name or getattr(model_class, '_table_name', model_class.__name__.lower())
        self.field_mappings = field_mappings or {}
    
    def serialize(self, instance: ModelType, **kwargs) -> Dict[str, Any]:
        """Serialize model to database-compatible dictionary"""
        try:
            # Get model data
            data = instance.model_dump(**kwargs)
            
            # Transform for database compatibility
            db_data = {}
            for field_name, value in data.items():
                # Apply field mapping
                db_field = self.field_mappings.get(field_name, field_name)
                
                # Transform value for database
                db_value = self._transform_for_database(value)
                db_data[db_field] = db_value
            
            return db_data
            
        except Exception as e:
            logger.error(f"Failed to serialize {self.model_class.__name__} for database: {str(e)}")
            raise
    
    def deserialize(self, data: Dict[str, Any], **kwargs) -> ModelType:
        """Deserialize database dictionary to model"""
        try:
            # Reverse field mappings
            reverse_mappings = {v: k for k, v in self.field_mappings.items()}
            
            # Transform from database format
            model_data = {}
            for db_field, value in data.items():
                # Apply reverse field mapping
                field_name = reverse_mappings.get(db_field, db_field)
                
                # Transform value from database
                model_value = self._transform_from_database(value, field_name)
                model_data[field_name] = model_value
            
            # Create model instance
            return self.model_class.model_validate(model_data)
            
        except Exception as e:
            logger.error(f"Failed to deserialize database data to {self.model_class.__name__}: {str(e)}")
            raise
    
    def _transform_for_database(self, value: Any) -> Any:
        """Transform value for database storage"""
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, time):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, Path):
            return str(value)
        elif isinstance(value, uuid.UUID):
            return str(value)
        elif isinstance(value, Enum):
            return value.value
        elif isinstance(value, BaseModel):
            return value.model_dump()
        elif isinstance(value, (list, dict)):
            return json.dumps(value, cls=CustomJSONEncoder)
        else:
            return value
    
    def _transform_from_database(self, value: Any, field_name: str) -> Any:
        """Transform value from database storage"""
        if value is None:
            return None
        
        # Get field info from model
        field_info = self.model_class.model_fields.get(field_name)
        if not field_info:
            return value
        
        field_type = field_info.annotation
        
        # Transform based on expected type
        if hasattr(field_type, '__origin__'):
            # Handle generic types (Optional, Union, List, etc.)
            if field_type.__origin__ is Union:
                # For Optional types, try each type
                for arg in field_type.__args__:
                    if arg is type(None):
                        continue
                    try:
                        return self._convert_to_type(value, arg)
                    except (ValueError, TypeError):
                        continue
            elif field_type.__origin__ in (list, List):
                # Handle list types
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value, object_hook=CustomJSONDecoder.object_hook)
                        return parsed if isinstance(parsed, list) else [parsed]
                    except json.JSONDecodeError:
                        return [value]
                return value if isinstance(value, list) else [value]
        else:
            return self._convert_to_type(value, field_type)
        
        return value
    
    def _convert_to_type(self, value: Any, target_type: Type) -> Any:
        """Convert value to target type"""
        if target_type == datetime:
            if isinstance(value, str):
                return datetime.fromisoformat(value)
        elif target_type == date:
            if isinstance(value, str):
                return date.fromisoformat(value)
        elif target_type == time:
            if isinstance(value, str):
                return time.fromisoformat(value)
        elif target_type == Decimal:
            return Decimal(str(value))
        elif target_type == Path:
            return Path(str(value))
        elif target_type == uuid.UUID:
            return uuid.UUID(str(value))
        elif issubclass(target_type, Enum):
            return target_type(value)
        elif issubclass(target_type, BaseModel):
            if isinstance(value, str):
                data = json.loads(value, object_hook=CustomJSONDecoder.object_hook)
                return target_type.model_validate(data)
            elif isinstance(value, dict):
                return target_type.model_validate(value)
        
        return value


# =============================================================================
# SCHEMA GENERATOR
# =============================================================================

class SchemaGenerator:
    """Generate schemas for models in various formats"""
    
    @staticmethod
    def generate_json_schema(model_class: Type[BaseModel], 
                           include_examples: bool = True) -> Dict[str, Any]:
        """Generate JSON schema for model"""
        schema = model_class.model_json_schema()
        
        if include_examples:
            # Add examples if not present
            if 'examples' not in schema:
                try:
                    # Create a sample instance
                    sample_data = SchemaGenerator._generate_sample_data(model_class)
                    sample_instance = model_class.model_validate(sample_data)
                    schema['examples'] = [sample_instance.model_dump()]
                except Exception as e:
                    logger.warning(f"Could not generate example for {model_class.__name__}: {e}")
        
        return schema
    
    @staticmethod
    def generate_database_schema(model_class: Type[BaseModel],
                               table_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate database schema for model"""
        table_name = table_name or getattr(model_class, '_table_name', model_class.__name__.lower())
        
        fields = []
        for field_name, field_info in model_class.model_fields.items():
            field_schema = {
                'name': field_name,
                'type': SchemaGenerator._get_sql_type(field_info.annotation),
                'nullable': not field_info.is_required(),
                'default': field_info.default if field_info.default is not None else None
            }
            fields.append(field_schema)
        
        return {
            'table_name': table_name,
            'fields': fields
        }
    
    @staticmethod
    def _generate_sample_data(model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Generate sample data for model"""
        data = {}
        
        for field_name, field_info in model_class.model_fields.items():
            if field_info.is_required():
                data[field_name] = SchemaGenerator._get_sample_value(field_info.annotation)
        
        return data
    
    @staticmethod
    def _get_sample_value(field_type: Type) -> Any:
        """Get sample value for field type"""
        if field_type == str:
            return "sample_string"
        elif field_type == int:
            return 42
        elif field_type == float:
            return 3.14
        elif field_type == bool:
            return True
        elif field_type == datetime:
            return datetime.now()
        elif field_type == date:
            return date.today()
        elif field_type == Decimal:
            return Decimal('10.50')
        elif field_type == Path:
            return Path("/sample/path")
        elif field_type == uuid.UUID:
            return uuid.uuid4()
        else:
            return None
    
    @staticmethod
    def _get_sql_type(python_type: Type) -> str:
        """Map Python type to SQL type"""
        type_mapping = {
            str: 'TEXT',
            int: 'INTEGER',
            float: 'REAL',
            bool: 'BOOLEAN',
            datetime: 'TIMESTAMP',
            date: 'DATE',
            time: 'TIME',
            Decimal: 'DECIMAL',
            uuid.UUID: 'UUID',
            Path: 'TEXT'
        }
        
        return type_mapping.get(python_type, 'TEXT')


# =============================================================================
# SERIALIZER FACTORY
# =============================================================================

class SerializerFactory:
    """Factory for creating serializers"""
    
    _serializers: Dict[SerializationFormat, Type[BaseSerializer]] = {
        SerializationFormat.JSON: JSONSerializer,
        SerializationFormat.DATABASE: DatabaseSerializer,
    }
    
    @classmethod
    def create_serializer(cls, format_type: SerializationFormat,
                         model_class: Type[ModelType],
                         **kwargs) -> BaseSerializer[ModelType]:
        """Create serializer for specified format"""
        serializer_class = cls._serializers.get(format_type)
        if not serializer_class:
            raise ValueError(f"Unsupported serialization format: {format_type}")
        
        return serializer_class(model_class, **kwargs)
    
    @classmethod
    def register_serializer(cls, format_type: SerializationFormat,
                          serializer_class: Type[BaseSerializer]):
        """Register custom serializer"""
        cls._serializers[format_type] = serializer_class


# =============================================================================
# BULK SERIALIZATION
# =============================================================================

class BulkSerializer:
    """Handle bulk serialization operations"""
    
    def __init__(self, serializer: BaseSerializer):
        self.serializer = serializer
    
    def serialize_many(self, instances: List[ModelType],
                      format_output: bool = True) -> Union[List[Any], str]:
        """Serialize multiple instances"""
        results = []
        
        for instance in instances:
            try:
                serialized = self.serializer.serialize(instance)
                results.append(serialized)
            except Exception as e:
                logger.error(f"Failed to serialize instance: {str(e)}")
                results.append(None)
        
        if format_output and isinstance(self.serializer, JSONSerializer):
            # Return as JSON array
            return json.dumps(results, cls=CustomJSONEncoder, indent=2)
        
        return results
    
    def deserialize_many(self, data_list: List[Any]) -> List[Optional[ModelType]]:
        """Deserialize multiple data items"""
        results = []
        
        for data in data_list:
            try:
                instance = self.serializer.deserialize(data)
                results.append(instance)
            except Exception as e:
                logger.error(f"Failed to deserialize data: {str(e)}")
                results.append(None)
        
        return results


# =============================================================================
# EXPORT/IMPORT UTILITIES
# =============================================================================

class ModelExporter:
    """Export models to various formats"""
    
    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class
    
    def export_to_file(self, instances: List[ModelType],
                      file_path: Path,
                      format_type: SerializationFormat = SerializationFormat.JSON,
                      **kwargs) -> bool:
        """Export instances to file"""
        try:
            serializer = SerializerFactory.create_serializer(format_type, self.model_class, **kwargs)
            bulk_serializer = BulkSerializer(serializer)
            
            if format_type == SerializationFormat.JSON:
                data = bulk_serializer.serialize_many(instances, format_output=True)
                file_path.write_text(data, encoding='utf-8')
            elif format_type == SerializationFormat.DATABASE:
                # Export as database insert statements
                data = bulk_serializer.serialize_many(instances, format_output=False)
                self._write_sql_inserts(data, file_path)
            
            logger.info(f"Exported {len(instances)} instances to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to {file_path}: {str(e)}")
            return False
    
    def _write_sql_inserts(self, data_list: List[Dict[str, Any]], file_path: Path):
        """Write SQL INSERT statements to file"""
        table_name = getattr(self.model_class, '_table_name', self.model_class.__name__.lower())
        
        with file_path.open('w', encoding='utf-8') as f:
            for data in data_list:
                if data:
                    columns = ', '.join(data.keys())
                    values = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in data.values()])
                    f.write(f"INSERT INTO {table_name} ({columns}) VALUES ({values});\n")


class ModelImporter:
    """Import models from various formats"""
    
    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class
    
    def import_from_file(self, file_path: Path,
                        format_type: SerializationFormat = SerializationFormat.JSON,
                        **kwargs) -> List[Optional[ModelType]]:
        """Import instances from file"""
        try:
            if format_type == SerializationFormat.JSON:
                data = json.loads(file_path.read_text(encoding='utf-8'),
                                object_hook=CustomJSONDecoder.object_hook)
            else:
                raise ValueError(f"Unsupported import format: {format_type}")
            
            serializer = SerializerFactory.create_serializer(format_type, self.model_class, **kwargs)
            bulk_serializer = BulkSerializer(serializer)
            
            instances = bulk_serializer.deserialize_many(data)
            logger.info(f"Imported {len([i for i in instances if i])} instances from {file_path}")
            return instances
            
        except Exception as e:
            logger.error(f"Failed to import from {file_path}: {str(e)}")
            return [] 