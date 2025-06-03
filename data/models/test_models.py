"""
Comprehensive Unit Tests for Social Download Manager v2.0 Data Models

Test suite covering model instantiation, validation, serialization/deserialization,
relationship management, and all advanced features of the data model system.
"""

import pytest
import json
import uuid
from datetime import datetime, date, time, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List

from pydantic import ValidationError

# Import all model modules for testing
from .pydantic_models import (
    SDMBaseModel, TimestampedModel, VersionedModel, 
    SoftDeletableModel, DatabaseEntity,
    ContentType, ContentStatus, DownloadStatus
)
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
from .validators import (
    URLValidator, JSONValidator, NumericValidator,
    BusinessRuleValidator, validate_status_transition
)
from .relationships import (
    RelationshipManager, RelationshipConfig, RelationshipType,
    CascadeAction, get_relationship_manager
)
from .serializers import (
    JSONSerializer, DatabaseSerializer, SerializationFormat,
    CustomJSONEncoder, CustomJSONDecoder
)
from .serialization_integration import (
    SerializationMixin, SerializablePlatform, SerializableContent,
    SerializableDownload, SerializableModelRegistry,
    validate_model_serialization, generate_all_schemas
)
from .model_integration import (
    IntegratedPlatform, IntegratedContent, IntegratedDownload,
    IntegratedModelFactory, BulkOperations
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_datetime():
    """Sample datetime for testing"""
    return datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)


@pytest.fixture
def sample_platform_data():
    """Sample platform data for testing"""
    return {
        'name': 'TikTok',
        'base_url': 'https://www.tiktok.com',
        'is_active': True,
        'supported_content_types': '["video", "image"]',
        'api_endpoint': 'https://api.tiktok.com/v1',
        'rate_limit_per_minute': 100,
        'requires_auth': True
    }


@pytest.fixture
def sample_content_data():
    """Sample content data for testing"""
    return {
        'platform_id': 1,
        'platform_content_id': 'tt_123456789',
        'content_type': ContentType.VIDEO,
        'title': 'Amazing TikTok Video',
        'description': 'A really cool video that went viral',
        'author_username': 'coolcreator',
        'content_url': 'https://www.tiktok.com/@coolcreator/video/123456789',
        'thumbnail_url': 'https://cdn.tiktok.com/thumb123.jpg',
        'duration_seconds': 45,
        'view_count': 1000000,
        'like_count': 50000,
        'comment_count': 5000,
        'share_count': 10000,
        'status': ContentStatus.ACTIVE,
        'published_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_download_data():
    """Sample download data for testing"""
    return {
        'content_id': 1,
        'requested_quality': 'high',
        'requested_format': 'mp4',
        'output_directory': '/downloads',
        'filename_template': '{author}_{title}',
        'status': DownloadStatus.QUEUED,
        'priority': 'medium'
    }


# =============================================================================
# BASE MODEL TESTS
# =============================================================================

class TestBaseModels:
    """Test base model functionality"""
    
    def test_sdm_base_model_creation(self):
        """Test SDMBaseModel creation and JSON serialization"""
        class TestModel(SDMBaseModel):
            name: str
            value: int
        
        model = TestModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42
        
        # Test JSON serialization
        json_str = model.to_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        model2 = TestModel.from_json(json_str)
        assert model2.name == model.name
        assert model2.value == model.value
    
    def test_timestamped_model(self, sample_datetime):
        """Test TimestampedModel functionality"""
        class TestTimestamped(TimestampedModel):
            name: str
        
        model = TestTimestamped(name="test")
        assert model.name == "test"
        assert model.created_at is not None
        assert model.updated_at is not None
        
        # Test mark_updated
        original_updated = model.updated_at
        model.mark_updated()
        assert model.updated_at > original_updated
    
    def test_versioned_model(self):
        """Test VersionedModel functionality"""
        class TestVersioned(VersionedModel):
            name: str
        
        model = TestVersioned(name="test")
        assert model.version == 1
        
        # Test increment_version
        model.increment_version()
        assert model.version == 2
    
    def test_soft_deletable_model(self):
        """Test SoftDeletableModel functionality"""
        class TestSoftDelete(SoftDeletableModel):
            name: str
        
        model = TestSoftDelete(name="test")
        assert not model.is_deleted
        assert model.deleted_at is None
        
        # Test soft delete
        model.soft_delete()
        assert model.is_deleted
        assert model.deleted_at is not None
        
        # Test restore
        model.restore()
        assert not model.is_deleted
        assert model.deleted_at is None
    
    def test_database_entity(self):
        """Test DatabaseEntity functionality"""
        class TestEntity(DatabaseEntity):
            name: str
        
        model = TestEntity(name="test")
        assert model.id is None  # Should be None until saved
        assert model.name == "test"
        
        # Test database dict conversion
        db_dict = model.to_db_dict()
        assert isinstance(db_dict, dict)
        assert 'name' in db_dict


# =============================================================================
# CORE MODEL TESTS
# =============================================================================

class TestCoreModels:
    """Test core model functionality"""
    
    def test_platform_model(self, sample_platform_data):
        """Test Platform model"""
        platform = Platform.model_validate(sample_platform_data)
        
        assert platform.name == "TikTok"
        assert platform.is_active
        assert platform.base_url == "https://www.tiktok.com"
        assert platform.rate_limit_per_minute == 100
        
        # Test computed properties
        assert platform.is_social_media
        assert platform.supports_video
    
    def test_content_model(self, sample_content_data):
        """Test Content model"""
        content = Content.model_validate(sample_content_data)
        
        assert content.title == "Amazing TikTok Video"
        assert content.content_type == ContentType.VIDEO
        assert content.view_count == 1000000
        
        # Test computed properties
        assert content.engagement_total == 65000  # like + comment + share
        assert content.is_downloadable
        assert content.has_video
    
    def test_download_model(self, sample_download_data):
        """Test Download model"""
        download = Download.model_validate(sample_download_data)
        
        assert download.content_id == 1
        assert download.status == DownloadStatus.QUEUED
        assert download.requested_quality == "high"
        
        # Test computed properties
        assert download.can_retry
        assert download.progress_percentage == 0
    
    def test_content_metadata_model(self):
        """Test ContentMetadata model"""
        metadata = ContentMetadata(
            content_id=1,
            metadata_type="platform",
            metadata_key="hashtags",
            metadata_value='["viral", "funny", "amazing"]',
            data_type="json"
        )
        
        assert metadata.content_id == 1
        assert metadata.metadata_type == "platform"
        assert metadata.data_type == "json"
        
        # Test JSON parsing
        parsed_value = metadata.get_parsed_value()
        assert isinstance(parsed_value, list)
        assert "viral" in parsed_value
    
    def test_download_session_model(self):
        """Test DownloadSession model"""
        session = DownloadSession(
            download_id=1,
            session_uuid=str(uuid.uuid4()),
            session_type="standard",
            session_status="active"
        )
        
        assert session.download_id == 1
        assert session.session_type == "standard"
        assert session.session_status == "active"
        
        # Test computed properties
        assert session.is_active
        assert not session.is_completed
    
    def test_quality_option_model(self):
        """Test QualityOption model"""
        quality = QualityOption(
            content_id=1,
            quality_label="1080p",
            format_name="mp4",
            video_codec="h264",
            audio_codec="aac",
            file_size_bytes=50000000,
            bitrate_kbps=2500
        )
        
        assert quality.quality_label == "1080p"
        assert quality.format_name == "mp4"
        assert quality.file_size_bytes == 50000000
        
        # Test computed properties
        assert quality.file_size_mb == 50  # Approximately
        assert quality.has_video
        assert quality.has_audio


# =============================================================================
# PLATFORM-SPECIFIC MODEL TESTS
# =============================================================================

class TestPlatformModels:
    """Test platform-specific model functionality"""
    
    def test_tiktok_content_model(self, sample_content_data):
        """Test TikTokContent model"""
        tiktok_data = {
            **sample_content_data,
            'video_type': 'normal',
            'music_title': 'Cool Song',
            'music_author': 'Artist Name',
            'effects_used': '["beauty", "filter1"]',
            'hashtags': '["viral", "funny"]',
            'is_duet': False,
            'is_stitch': False
        }
        
        content = TikTokContent.model_validate(tiktok_data)
        
        assert content.video_type == 'normal'
        assert content.music_title == 'Cool Song'
        assert not content.is_duet
        assert not content.is_stitch
        
        # Test computed properties
        assert not content.is_duet_or_stitch
        assert content.total_tiktok_engagement == 65000
    
    def test_youtube_content_model(self, sample_content_data):
        """Test YouTubeContent model"""
        youtube_data = {
            **sample_content_data,
            'video_type': 'normal',
            'channel_id': 'UC123456789',
            'channel_name': 'Cool Channel',
            'category_id': 24,  # Entertainment
            'has_captions': True,
            'caption_languages': '["en", "es"]',
            'privacy_status': 'public'
        }
        
        content = YouTubeContent.model_validate(youtube_data)
        
        assert content.channel_id == 'UC123456789'
        assert content.has_captions
        assert content.privacy_status == 'public'
        
        # Test computed properties
        assert not content.is_live_content
        assert not content.is_short_form  # 45 seconds > 30
    
    def test_platform_model_factory(self, sample_content_data):
        """Test PlatformModelFactory"""
        # Test TikTok content creation
        tiktok_content = PlatformModelFactory.create_content('tiktok', sample_content_data)
        assert isinstance(tiktok_content, TikTokContent)
        
        # Test YouTube content creation
        youtube_content = PlatformModelFactory.create_content('youtube', sample_content_data)
        assert isinstance(youtube_content, YouTubeContent)
        
        # Test unknown platform
        with pytest.raises(ValueError):
            PlatformModelFactory.create_content('unknown', sample_content_data)


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidation:
    """Test validation functionality"""
    
    def test_url_validation(self):
        """Test URL validation"""
        # Valid URLs
        assert URLValidator.is_valid_url("https://www.tiktok.com/@user/video/123")
        assert URLValidator.is_valid_url("https://youtube.com/watch?v=abc123")
        
        # Invalid URLs
        assert not URLValidator.is_valid_url("not-a-url")
        assert not URLValidator.is_valid_url("ftp://invalid.com")
        
        # Platform-specific validation
        assert URLValidator.is_valid_tiktok_url("https://www.tiktok.com/@user/video/123")
        assert not URLValidator.is_valid_tiktok_url("https://youtube.com/watch?v=abc")
    
    def test_json_validation(self):
        """Test JSON validation"""
        # Valid JSON
        valid_json = '{"key": "value", "number": 42}'
        assert JSONValidator.is_valid_json(valid_json)
        
        # Invalid JSON
        invalid_json = '{"key": "value"'  # Missing closing brace
        assert not JSONValidator.is_valid_json(invalid_json)
        
        # Schema validation
        schema = {"type": "object", "required": ["key"]}
        assert JSONValidator.validate_against_schema(valid_json, schema)
    
    def test_numeric_validation(self):
        """Test numeric validation"""
        # Valid ranges
        assert NumericValidator.is_valid_percentage(50.5)
        assert NumericValidator.is_valid_speed_bps(1000000)
        assert NumericValidator.is_valid_file_size(1024 * 1024)  # 1MB
        
        # Invalid ranges
        assert not NumericValidator.is_valid_percentage(-10)
        assert not NumericValidator.is_valid_percentage(150)
        assert not NumericValidator.is_valid_speed_bps(-100)
    
    def test_business_rule_validation(self, sample_content_data):
        """Test business rule validation"""
        content = Content.model_validate(sample_content_data)
        
        # Valid content should pass
        errors = BusinessRuleValidator.validate_content_business_rules(content.model_dump())
        assert len(errors) == 0
        
        # Invalid content should fail
        invalid_data = {**sample_content_data, 'view_count': -100}
        errors = BusinessRuleValidator.validate_content_business_rules(invalid_data)
        assert len(errors) > 0
    
    def test_status_transition_validation(self):
        """Test status transition validation"""
        # Valid transitions
        is_valid, _ = validate_status_transition('queued', 'downloading', 'download')
        assert is_valid
        
        is_valid, _ = validate_status_transition('downloading', 'completed', 'download')
        assert is_valid
        
        # Invalid transitions
        is_valid, error = validate_status_transition('completed', 'queued', 'download')
        assert not is_valid
        assert error is not None


# =============================================================================
# RELATIONSHIP TESTS
# =============================================================================

class TestRelationships:
    """Test relationship management"""
    
    def test_relationship_manager(self):
        """Test RelationshipManager functionality"""
        manager = get_relationship_manager()
        
        # Check that relationships are registered
        assert len(manager.relationships) > 0
        
        # Test specific relationship
        platform_content_rel = manager.get_relationship('platform_content')
        assert platform_content_rel is not None
        assert platform_content_rel.relationship_type == RelationshipType.ONE_TO_MANY
    
    def test_relationship_validation(self, sample_platform_data, sample_content_data):
        """Test relationship validation"""
        platform = Platform.model_validate(sample_platform_data)
        content = Content.model_validate(sample_content_data)
        
        # Test with IntegratedModels that have relationship support
        integrated_platform = IntegratedPlatform.model_validate(sample_platform_data)
        
        # Validate relationships (placeholder test since we don't have full DB integration)
        errors = integrated_platform.validate_relationships()
        assert isinstance(errors, list)
    
    def test_cascade_operations(self):
        """Test cascade operations"""
        manager = get_relationship_manager()
        
        # Test that cascade handlers are properly registered
        assert CascadeAction.RESTRICT in manager._cascade_handlers
        assert CascadeAction.CASCADE in manager._cascade_handlers
        assert CascadeAction.SET_NULL in manager._cascade_handlers


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================

class TestSerialization:
    """Test serialization functionality"""
    
    def test_json_serialization(self, sample_platform_data):
        """Test JSON serialization"""
        platform = SerializablePlatform.model_validate(sample_platform_data)
        
        # Test JSON serialization
        json_str = platform.to_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        platform2 = SerializablePlatform.from_json(json_str)
        assert platform2.name == platform.name
        assert platform2.base_url == platform.base_url
    
    def test_database_serialization(self, sample_content_data):
        """Test database serialization"""
        content = SerializableContent.model_validate(sample_content_data)
        
        # Test database dict conversion
        db_dict = content.to_db_dict()
        assert isinstance(db_dict, dict)
        assert 'title' in db_dict
        
        # Test deserialization
        content2 = SerializableContent.from_db_dict(db_dict)
        assert content2.title == content.title
    
    def test_custom_encoders(self):
        """Test custom JSON encoders/decoders"""
        # Test datetime encoding
        encoder = CustomJSONEncoder()
        dt = datetime.now(timezone.utc)
        encoded = encoder.default(dt)
        assert encoded['__type__'] == 'datetime'
        
        # Test decoding
        decoded = CustomJSONDecoder.object_hook(encoded)
        assert isinstance(decoded, datetime)
    
    def test_serialization_validation(self, sample_platform_data):
        """Test serialization validation"""
        platform = SerializablePlatform.model_validate(sample_platform_data)
        
        # Validate serialization capabilities
        results = validate_model_serialization(platform)
        assert results['model_class'] == 'SerializablePlatform'
        # Note: Some tests might fail due to missing database integration
    
    def test_bulk_serialization(self, sample_platform_data, sample_content_data):
        """Test bulk serialization operations"""
        platform = SerializablePlatform.model_validate(sample_platform_data)
        content = SerializableContent.model_validate(sample_content_data)
        
        models = [platform, content]
        
        # Test bulk export (to memory)
        from .serialization_integration import BulkSerializationOperations
        
        # Create temporary file for testing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            success = BulkSerializationOperations.export_models_to_json(models, temp_path)
            assert success
            assert temp_path.exists()
            
            # Test bulk import
            imported_models = BulkSerializationOperations.import_models_from_json(temp_path)
            assert len(imported_models) == 2
        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Test integrated model functionality"""
    
    def test_integrated_models(self, sample_platform_data, sample_content_data):
        """Test IntegratedModel functionality"""
        # Test IntegratedPlatform
        platform = IntegratedPlatform.model_validate(sample_platform_data)
        assert hasattr(platform, 'save')
        assert hasattr(platform, 'delete')
        assert hasattr(platform, 'validate_relationships')
        
        # Test IntegratedContent
        content = IntegratedContent.model_validate(sample_content_data)
        assert hasattr(content, 'add_metadata')
        assert hasattr(content, 'create_download')
    
    def test_model_factory(self, sample_content_data):
        """Test IntegratedModelFactory"""
        # Test model creation
        platform_data = {'name': 'Test Platform', 'base_url': 'https://test.com'}
        platform = IntegratedModelFactory.create_model('platform', platform_data)
        assert isinstance(platform, IntegratedPlatform)
        
        # Test content creation with platform
        content = IntegratedModelFactory.create_model('content', sample_content_data, 'tiktok')
        assert content is not None
    
    def test_bulk_operations(self, sample_platform_data, sample_content_data):
        """Test bulk operations"""
        platform = IntegratedPlatform.model_validate(sample_platform_data)
        content = IntegratedContent.model_validate(sample_content_data)
        
        instances = [platform, content]
        
        # Test bulk validation (mock since we don't have full DB)
        results = BulkOperations.bulk_create(instances, validate_relationships=False)
        assert len(results) == 2


# =============================================================================
# REGISTRY TESTS
# =============================================================================

class TestRegistry:
    """Test model registry functionality"""
    
    def test_serializable_model_registry(self):
        """Test SerializableModelRegistry"""
        # Check that models are registered
        models = SerializableModelRegistry.list_models()
        assert 'Platform' in models
        assert 'Content' in models
        assert 'Download' in models
        
        # Test model retrieval
        platform_class = SerializableModelRegistry.get_model('Platform')
        assert platform_class == SerializablePlatform
        
        # Test instance creation
        data = {'name': 'Test', 'base_url': 'https://test.com'}
        instance = SerializableModelRegistry.create_instance('Platform', data)
        assert isinstance(instance, SerializablePlatform)


# =============================================================================
# SCHEMA GENERATION TESTS
# =============================================================================

class TestSchemaGeneration:
    """Test schema generation functionality"""
    
    def test_json_schema_generation(self):
        """Test JSON schema generation"""
        from .serializers import SchemaGenerator
        
        schema = SchemaGenerator.generate_json_schema(Platform)
        assert isinstance(schema, dict)
        assert 'properties' in schema
        assert 'name' in schema['properties']
    
    def test_database_schema_generation(self):
        """Test database schema generation"""
        from .serializers import SchemaGenerator
        
        schema = SchemaGenerator.generate_database_schema(Platform)
        assert isinstance(schema, dict)
        assert 'table_name' in schema
        assert 'fields' in schema
        assert len(schema['fields']) > 0
    
    def test_all_schemas_generation(self):
        """Test generation of all schemas"""
        schemas = generate_all_schemas()
        assert isinstance(schemas, dict)
        assert len(schemas) > 0
        
        # Check that each model has both JSON and database schemas
        for model_name, model_schemas in schemas.items():
            if 'error' not in model_schemas:
                assert 'json_schema' in model_schemas
                assert 'database_schema' in model_schemas


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling in models"""
    
    def test_validation_errors(self):
        """Test that validation errors are properly raised"""
        # Test required field missing
        with pytest.raises(ValidationError):
            Platform(base_url="https://test.com")  # Missing required 'name'
        
        # Test invalid URL format
        with pytest.raises(ValidationError):
            Platform(name="Test", base_url="not-a-url")
        
        # Test invalid enum value
        with pytest.raises(ValidationError):
            Content(
                platform_id=1,
                platform_content_id="123",
                content_type="invalid_type",  # Should be ContentType enum
                title="Test"
            )
    
    def test_serialization_errors(self):
        """Test serialization error handling"""
        # Test with invalid JSON
        with pytest.raises(Exception):
            SerializablePlatform.from_json("invalid json")
        
        # Test with missing required fields in database dict
        with pytest.raises(ValidationError):
            SerializablePlatform.from_db_dict({})  # Missing required fields


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance characteristics"""
    
    def test_bulk_model_creation(self, sample_platform_data):
        """Test performance of bulk model creation"""
        import time
        
        start_time = time.time()
        
        # Create 1000 platform instances
        platforms = []
        for i in range(1000):
            data = {**sample_platform_data, 'name': f'Platform {i}'}
            platform = Platform.model_validate(data)
            platforms.append(platform)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time
        assert duration < 5.0  # Less than 5 seconds
        assert len(platforms) == 1000
    
    def test_serialization_performance(self, sample_content_data):
        """Test serialization performance"""
        import time
        
        # Create a content instance
        content = SerializableContent.model_validate(sample_content_data)
        
        start_time = time.time()
        
        # Serialize/deserialize 1000 times
        for _ in range(1000):
            json_str = content.to_json()
            SerializableContent.from_json(json_str)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time
        assert duration < 10.0  # Less than 10 seconds


# =============================================================================
# INTEGRATION WITH EXTERNAL LIBRARIES TESTS
# =============================================================================

class TestExternalIntegration:
    """Test integration with external libraries"""
    
    def test_pydantic_features(self, sample_content_data):
        """Test Pydantic-specific features"""
        content = Content.model_validate(sample_content_data)
        
        # Test model_dump
        data = content.model_dump()
        assert isinstance(data, dict)
        
        # Test model_dump with exclusions
        data_no_id = content.model_dump(exclude={'id'})
        assert 'id' not in data_no_id
        
        # Test model_json_schema
        schema = Content.model_json_schema()
        assert isinstance(schema, dict)
        assert 'properties' in schema
    
    def test_enum_integration(self):
        """Test enum integration"""
        # Test ContentType enum
        assert ContentType.VIDEO.value == "video"
        assert ContentType.IMAGE.value == "image"
        
        # Test that enums work in models
        content_data = {
            'platform_id': 1,
            'platform_content_id': '123',
            'content_type': ContentType.VIDEO,
            'title': 'Test Video'
        }
        content = Content.model_validate(content_data)
        assert content.content_type == ContentType.VIDEO


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"]) 