"""
Test Fixtures and Data Factory System

This module provides comprehensive test data management including:
- Factory pattern for test data creation
- Test data fixtures and templates
- Data cleanup and lifecycle management
- Realistic test data generation
- Bulk data creation utilities
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# Import base test infrastructure
from .test_base import DatabaseTestCase, TestConfig

# Database and model components
from data.models import (
    ContentModel, ContentType, ContentStatus, PlatformType
)
from data.models.repositories import ContentRepository

T = TypeVar('T')


@dataclass
class TestDataTemplate:
    """Template for generating test data"""
    
    name: str
    description: str
    data_factory: Callable[[], Any]
    cleanup_factory: Optional[Callable[[Any], None]] = None
    dependencies: List[str] = field(default_factory=list)
    
    def generate(self) -> Any:
        """Generate test data using the factory"""
        return self.data_factory()
    
    def cleanup(self, data: Any) -> None:
        """Clean up test data"""
        if self.cleanup_factory:
            self.cleanup_factory(data)


class DataFactory(ABC, Generic[T]):
    """Abstract base class for data factories"""
    
    def __init__(self, **defaults):
        self.defaults = defaults
        self._sequence_counters: Dict[str, int] = {}
    
    @abstractmethod
    def create(self, **overrides) -> T:
        """Create a single instance with optional field overrides"""
        pass
    
    def create_batch(self, count: int, **overrides) -> List[T]:
        """Create multiple instances"""
        return [self.create(**overrides) for _ in range(count)]
    
    def sequence(self, key: str, start: int = 1) -> int:
        """Generate sequential numbers for unique fields"""
        if key not in self._sequence_counters:
            self._sequence_counters[key] = start
        else:
            self._sequence_counters[key] += 1
        return self._sequence_counters[key]
    
    def reset_sequences(self) -> None:
        """Reset all sequence counters"""
        self._sequence_counters.clear()


class ContentModelFactory(DataFactory[ContentModel]):
    """Factory for creating ContentModel test instances"""
    
    def __init__(self, **defaults):
        default_values = {
            'platform': PlatformType.TIKTOK,
            'content_type': ContentType.VIDEO,
            'status': ContentStatus.PENDING,
            'author': 'Test Author',
            'title': 'Test Content',
            'description': 'A test content description',
            'duration': 30,
            'file_size': 1024 * 1024,  # 1MB
            'thumbnail_url': None,
            'download_progress': 0,
            'retry_count': 0,
            'error_message': None,
            'metadata': {},
        }
        default_values.update(defaults)
        super().__init__(**default_values)
    
    def create(self, **overrides) -> ContentModel:
        """Create a ContentModel instance"""
        # Merge defaults with overrides
        data = {**self.defaults, **overrides}
        
        # Generate unique fields if not provided
        if 'url' not in data:
            seq = self.sequence('url')
            platform = data['platform'].value.lower()
            data['url'] = f"https://{platform}.com/test-video-{seq}"
        
        if 'platform_id' not in data:
            seq = self.sequence('platform_id')
            data['platform_id'] = f"test_{seq}_{self._generate_random_string(8)}"
        
        if 'title' in data and data['title'] == 'Test Content':
            seq = self.sequence('title')
            data['title'] = f"Test Content {seq}"
        
        return ContentModel(**data)
    
    def create_tiktok_video(self, **overrides) -> ContentModel:
        """Create a TikTok video content"""
        defaults = {
            'platform': PlatformType.TIKTOK,
            'content_type': ContentType.VIDEO,
            'duration': random.randint(15, 60),
            'title': f"TikTok Video {self.sequence('tiktok')}",
            'author': f"TikTokCreator{random.randint(1, 1000)}"
        }
        return self.create(**{**defaults, **overrides})
    
    def create_youtube_video(self, **overrides) -> ContentModel:
        """Create a YouTube video content"""
        defaults = {
            'platform': PlatformType.YOUTUBE,
            'content_type': ContentType.VIDEO,
            'duration': random.randint(60, 3600),  # 1 minute to 1 hour
            'title': f"YouTube Video {self.sequence('youtube')}",
            'author': f"YouTuber{random.randint(1, 1000)}",
            'description': self._generate_lorem_ipsum(50, 200)
        }
        return self.create(**{**defaults, **overrides})
    
    def create_instagram_post(self, **overrides) -> ContentModel:
        """Create an Instagram post content"""
        content_type = random.choice([ContentType.IMAGE, ContentType.VIDEO])
        defaults = {
            'platform': PlatformType.INSTAGRAM,
            'content_type': content_type,
            'duration': random.randint(15, 60) if content_type == ContentType.VIDEO else None,
            'title': f"Instagram Post {self.sequence('instagram')}",
            'author': f"@insta_user_{random.randint(1, 1000)}",
            'description': self._generate_lorem_ipsum(10, 100)
        }
        return self.create(**{**defaults, **overrides})
    
    def create_completed_content(self, **overrides) -> ContentModel:
        """Create completed content with file path"""
        seq = self.sequence('completed')
        defaults = {
            'status': ContentStatus.COMPLETED,
            'download_progress': 100,
            'file_path': f"/downloads/test_content_{seq}.mp4",
            'file_size': random.randint(1024*1024, 100*1024*1024),  # 1MB to 100MB
            'downloaded_at': datetime.now()
        }
        return self.create(**{**defaults, **overrides})
    
    def create_failed_content(self, **overrides) -> ContentModel:
        """Create failed content with error information"""
        error_messages = [
            "Network timeout during download",
            "Video not available",
            "Private content access denied",
            "File size exceeds limit",
            "Unsupported format"
        ]
        defaults = {
            'status': ContentStatus.FAILED,
            'error_message': random.choice(error_messages),
            'retry_count': random.randint(1, 3)
        }
        return self.create(**{**defaults, **overrides})
    
    def create_downloading_content(self, **overrides) -> ContentModel:
        """Create content in downloading state"""
        defaults = {
            'status': ContentStatus.DOWNLOADING,
            'download_progress': random.randint(1, 99),
            'download_started_at': datetime.now() - timedelta(minutes=random.randint(1, 30))
        }
        return self.create(**{**defaults, **overrides})
    
    def _generate_random_string(self, length: int) -> str:
        """Generate a random string"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def _generate_lorem_ipsum(self, min_words: int, max_words: int) -> str:
        """Generate lorem ipsum text"""
        words = [
            "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit",
            "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore",
            "magna", "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud",
            "exercitation", "ullamco", "laboris", "nisi", "aliquip", "ex", "ea", "commodo",
            "consequat", "duis", "aute", "irure", "reprehenderit", "in", "voluptate",
            "velit", "esse", "cillum", "fugiat", "nulla", "pariatur", "excepteur", "sint",
            "occaecat", "cupidatat", "non", "proident", "sunt", "culpa", "qui", "officia",
            "deserunt", "mollit", "anim", "id", "est", "laborum"
        ]
        
        word_count = random.randint(min_words, max_words)
        selected_words = random.choices(words, k=word_count)
        return ' '.join(selected_words).capitalize() + '.'


class FixtureManager:
    """Manages test fixtures and their lifecycle"""
    
    def __init__(self):
        self.templates: Dict[str, TestDataTemplate] = {}
        self.instances: Dict[str, List[Any]] = {}
        self.cleanup_order: List[str] = []
    
    def register_template(self, template: TestDataTemplate) -> None:
        """Register a test data template"""
        self.templates[template.name] = template
    
    def create_fixture(self, template_name: str, count: int = 1) -> List[Any]:
        """Create fixture instances from a template"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        
        # Check dependencies
        for dep in template.dependencies:
            if dep not in self.instances:
                self.create_fixture(dep)
        
        # Create instances
        instances = []
        for _ in range(count):
            instance = template.generate()
            instances.append(instance)
        
        # Track instances for cleanup
        if template_name not in self.instances:
            self.instances[template_name] = []
            self.cleanup_order.append(template_name)
        
        self.instances[template_name].extend(instances)
        
        return instances
    
    def get_fixture(self, template_name: str) -> List[Any]:
        """Get existing fixture instances"""
        return self.instances.get(template_name, [])
    
    def cleanup_all(self) -> None:
        """Clean up all fixture instances in reverse order"""
        for template_name in reversed(self.cleanup_order):
            self.cleanup_fixture(template_name)
        
        self.instances.clear()
        self.cleanup_order.clear()
    
    def cleanup_fixture(self, template_name: str) -> None:
        """Clean up specific fixture instances"""
        if template_name not in self.instances:
            return
        
        template = self.templates[template_name]
        instances = self.instances[template_name]
        
        for instance in instances:
            try:
                template.cleanup(instance)
            except Exception:
                pass  # Ignore cleanup errors
        
        del self.instances[template_name]
        if template_name in self.cleanup_order:
            self.cleanup_order.remove(template_name)


class DatabaseFixtureTestCase(DatabaseTestCase):
    """Base test case with fixture management support"""
    
    def _custom_setup(self):
        """Setup fixture management"""
        super()._custom_setup()
        
        # Initialize fixture manager
        self.fixture_manager = FixtureManager()
        self.content_factory = ContentModelFactory()
        
        # Setup repository if available
        if hasattr(self, 'repository'):
            self._setup_repository_fixtures()
    
    def _custom_teardown(self):
        """Cleanup fixtures"""
        try:
            self.fixture_manager.cleanup_all()
        except Exception:
            pass
        super()._custom_teardown()
    
    def _setup_repository_fixtures(self):
        """Setup repository-based fixtures"""
        # Content fixture templates
        self.fixture_manager.register_template(TestDataTemplate(
            name="content_basic",
            description="Basic content instances",
            data_factory=lambda: self.content_factory.create(),
            cleanup_factory=lambda content: self._cleanup_content(content)
        ))
        
        self.fixture_manager.register_template(TestDataTemplate(
            name="content_tiktok",
            description="TikTok content instances",
            data_factory=lambda: self.content_factory.create_tiktok_video(),
            cleanup_factory=lambda content: self._cleanup_content(content)
        ))
        
        self.fixture_manager.register_template(TestDataTemplate(
            name="content_youtube", 
            description="YouTube content instances",
            data_factory=lambda: self.content_factory.create_youtube_video(),
            cleanup_factory=lambda content: self._cleanup_content(content)
        ))
        
        self.fixture_manager.register_template(TestDataTemplate(
            name="content_completed",
            description="Completed content instances",
            data_factory=lambda: self.content_factory.create_completed_content(),
            cleanup_factory=lambda content: self._cleanup_content(content)
        ))
        
        self.fixture_manager.register_template(TestDataTemplate(
            name="content_failed",
            description="Failed content instances",
            data_factory=lambda: self.content_factory.create_failed_content(),
            cleanup_factory=lambda content: self._cleanup_content(content)
        ))
    
    def _cleanup_content(self, content: ContentModel) -> None:
        """Clean up content from repository"""
        if hasattr(self, 'repository') and content.id:
            try:
                self.repository.delete_by_id(content.id)
            except Exception:
                pass
    
    def create_fixture(self, template_name: str, count: int = 1, save_to_db: bool = True) -> List[Any]:
        """Create fixture and optionally save to database"""
        instances = self.fixture_manager.create_fixture(template_name, count)
        
        if save_to_db and hasattr(self, 'repository'):
            saved_instances = []
            for instance in instances:
                if isinstance(instance, ContentModel):
                    saved_instance = self.repository.save(instance)
                    saved_instances.append(saved_instance)
                else:
                    saved_instances.append(instance)
            return saved_instances
        
        return instances
    
    def get_fixture(self, template_name: str) -> List[Any]:
        """Get existing fixture instances"""
        return self.fixture_manager.get_fixture(template_name)


class TestContentModelFactory(DatabaseFixtureTestCase):
    """Test the ContentModelFactory functionality"""
    
    def _custom_setup(self):
        """Setup for factory testing"""
        super()._custom_setup()
        
        # Setup repository for testing
        from data.models import ContentModelManager
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        self.repository = ContentRepository(self.model_manager)
        
        # Now setup fixtures
        self._setup_repository_fixtures()
    
    def test_basic_content_creation(self):
        """Test basic content model creation"""
        content = self.content_factory.create()
        
        # Verify required fields
        self.assertIsNotNone(content.url)
        self.assertIsNotNone(content.platform)
        self.assertIsNotNone(content.content_type)
        self.assertIsNotNone(content.title)
        self.assertIsNotNone(content.author)
        self.assertIsNotNone(content.platform_id)
        
        # Verify defaults
        self.assertEqual(content.status, ContentStatus.PENDING)
        self.assertEqual(content.download_progress, 0)
        self.assertEqual(content.retry_count, 0)
    
    def test_content_creation_with_overrides(self):
        """Test content creation with field overrides"""
        custom_title = "Custom Test Title"
        custom_status = ContentStatus.COMPLETED
        
        content = self.content_factory.create(
            title=custom_title,
            status=custom_status,
            download_progress=100
        )
        
        self.assertEqual(content.title, custom_title)
        self.assertEqual(content.status, custom_status)
        self.assertEqual(content.download_progress, 100)
    
    def test_platform_specific_creation(self):
        """Test platform-specific content creation"""
        # TikTok video
        tiktok_content = self.content_factory.create_tiktok_video()
        self.assertEqual(tiktok_content.platform, PlatformType.TIKTOK)
        self.assertEqual(tiktok_content.content_type, ContentType.VIDEO)
        self.assertGreaterEqual(tiktok_content.duration, 15)
        self.assertLessEqual(tiktok_content.duration, 60)
        
        # YouTube video
        youtube_content = self.content_factory.create_youtube_video()
        self.assertEqual(youtube_content.platform, PlatformType.YOUTUBE)
        self.assertEqual(youtube_content.content_type, ContentType.VIDEO)
        self.assertGreaterEqual(youtube_content.duration, 60)
        self.assertIsNotNone(youtube_content.description)
        
        # Instagram post
        instagram_content = self.content_factory.create_instagram_post()
        self.assertEqual(instagram_content.platform, PlatformType.INSTAGRAM)
        self.assertIn(instagram_content.content_type, [ContentType.IMAGE, ContentType.VIDEO])
    
    def test_status_specific_creation(self):
        """Test status-specific content creation"""
        # Completed content
        completed = self.content_factory.create_completed_content()
        self.assertEqual(completed.status, ContentStatus.COMPLETED)
        self.assertEqual(completed.download_progress, 100)
        self.assertIsNotNone(completed.file_path)
        self.assertGreater(completed.file_size, 0)
        
        # Failed content
        failed = self.content_factory.create_failed_content()
        self.assertEqual(failed.status, ContentStatus.FAILED)
        self.assertIsNotNone(failed.error_message)
        self.assertGreater(failed.retry_count, 0)
        
        # Downloading content
        downloading = self.content_factory.create_downloading_content()
        self.assertEqual(downloading.status, ContentStatus.DOWNLOADING)
        self.assertGreater(downloading.download_progress, 0)
        self.assertLess(downloading.download_progress, 100)
    
    def test_batch_creation(self):
        """Test batch content creation"""
        batch_size = 5
        contents = self.content_factory.create_batch(batch_size)
        
        self.assertEqual(len(contents), batch_size)
        
        # Verify all are unique
        urls = [content.url for content in contents]
        platform_ids = [content.platform_id for content in contents]
        
        self.assertEqual(len(set(urls)), batch_size)
        self.assertEqual(len(set(platform_ids)), batch_size)
    
    def test_sequence_generation(self):
        """Test sequence counter functionality"""
        # Reset sequences
        self.content_factory.reset_sequences()
        
        # Create multiple contents and verify sequence
        contents = []
        for i in range(3):
            content = self.content_factory.create()
            contents.append(content)
        
        # Verify sequential numbering in URLs and titles
        for i, content in enumerate(contents, 1):
            self.assertIn(str(i), content.url)
            self.assertIn(str(i), content.title)


class TestFixtureManager(DatabaseFixtureTestCase):
    """Test the FixtureManager functionality"""
    
    def _custom_setup(self):
        """Setup for fixture manager testing"""
        super()._custom_setup()
        
        # Setup repository
        from data.models import ContentModelManager
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        self.repository = ContentRepository(self.model_manager)
        
        # Setup fixtures
        self._setup_repository_fixtures()
    
    def test_fixture_creation_and_retrieval(self):
        """Test fixture creation and retrieval"""
        # Create fixtures
        tiktok_fixtures = self.create_fixture("content_tiktok", count=3, save_to_db=True)
        
        self.assertEqual(len(tiktok_fixtures), 3)
        
        # Verify all are saved to database
        for content in tiktok_fixtures:
            self.assertIsNotNone(content.id)
            self.assertEqual(content.platform, PlatformType.TIKTOK)
        
        # Retrieve fixtures
        retrieved_fixtures = self.get_fixture("content_tiktok")
        self.assertEqual(len(retrieved_fixtures), 3)
    
    def test_multiple_fixture_types(self):
        """Test creating multiple types of fixtures"""
        # Create different types of fixtures
        basic_fixtures = self.create_fixture("content_basic", count=2, save_to_db=True)
        completed_fixtures = self.create_fixture("content_completed", count=2, save_to_db=True)
        failed_fixtures = self.create_fixture("content_failed", count=1, save_to_db=True)
        
        # Verify counts
        self.assertEqual(len(basic_fixtures), 2)
        self.assertEqual(len(completed_fixtures), 2)
        self.assertEqual(len(failed_fixtures), 1)
        
        # Verify different statuses
        for content in completed_fixtures:
            self.assertEqual(content.status, ContentStatus.COMPLETED)
        
        for content in failed_fixtures:
            self.assertEqual(content.status, ContentStatus.FAILED)
        
        # Verify total count in database
        total_count = self.repository.count()
        self.assertEqual(total_count, 5)
    
    def test_fixture_cleanup(self):
        """Test fixture cleanup functionality"""
        # Create fixtures
        fixtures = self.create_fixture("content_basic", count=3, save_to_db=True)
        
        # Verify they exist in database
        initial_count = self.repository.count()
        self.assertEqual(initial_count, 3)
        
        # Manual cleanup should remove them
        self.fixture_manager.cleanup_all()
        
        # Verify they're removed from database
        final_count = self.repository.count()
        self.assertEqual(final_count, 0)


class TestDatasetGeneration(DatabaseFixtureTestCase):
    """Test large dataset generation for performance testing"""
    
    def _custom_setup(self):
        """Setup for dataset generation testing"""
        super()._custom_setup()
        
        # Setup repository
        from data.models import ContentModelManager
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        self.repository = ContentRepository(self.model_manager)
        
        # Setup fixtures
        self._setup_repository_fixtures()
    
    def test_large_dataset_generation(self):
        """Test generation of large test datasets"""
        # Generate dataset with mixed content types
        dataset_size = 100
        
        # Create mixed platform content
        platform_distribution = {
            PlatformType.TIKTOK: dataset_size // 3,
            PlatformType.YOUTUBE: dataset_size // 3,
            PlatformType.INSTAGRAM: dataset_size // 3 + dataset_size % 3
        }
        
        all_content = []
        
        for platform, count in platform_distribution.items():
            if platform == PlatformType.TIKTOK:
                content_batch = [self.content_factory.create_tiktok_video() for _ in range(count)]
            elif platform == PlatformType.YOUTUBE:
                content_batch = [self.content_factory.create_youtube_video() for _ in range(count)]
            else:  # Instagram
                content_batch = [self.content_factory.create_instagram_post() for _ in range(count)]
            
            all_content.extend(content_batch)
        
        # Save to database
        saved_content = []
        for content in all_content:
            saved = self.repository.save(content)
            saved_content.append(saved)
        
        # Verify dataset
        self.assertEqual(len(saved_content), dataset_size)
        
        # Verify platform distribution
        stats = self.repository.get_platform_stats()
        for platform, expected_count in platform_distribution.items():
            self.assertEqual(stats[platform]['total'], expected_count)
        
        # Clean up
        for content in saved_content:
            self.repository.delete_by_id(content.id)
    
    def test_realistic_workflow_dataset(self):
        """Test generation of realistic workflow dataset"""
        # Create content in various stages of processing
        workflow_stages = {
            ContentStatus.PENDING: 20,
            ContentStatus.DOWNLOADING: 10,
            ContentStatus.COMPLETED: 50,
            ContentStatus.FAILED: 5,
        }
        
        all_content = []
        
        for status, count in workflow_stages.items():
            for _ in range(count):
                if status == ContentStatus.COMPLETED:
                    content = self.content_factory.create_completed_content()
                elif status == ContentStatus.FAILED:
                    content = self.content_factory.create_failed_content()
                elif status == ContentStatus.DOWNLOADING:
                    content = self.content_factory.create_downloading_content()
                else:  # PENDING
                    content = self.content_factory.create()
                
                saved_content = self.repository.save(content)
                all_content.append(saved_content)
        
        # Verify workflow distribution
        for status, expected_count in workflow_stages.items():
            actual_content = self.repository.find_by_status(status)
            self.assertEqual(len(actual_content), expected_count)
        
        # Test search functionality with realistic data
        search_results = self.repository.search_content("Test")
        self.assertGreater(len(search_results), 0)
        
        # Clean up
        for content in all_content:
            self.repository.delete_by_id(content.id)


if __name__ == '__main__':
    unittest.main() 