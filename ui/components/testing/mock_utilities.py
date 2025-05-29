"""
Mock Utilities for Component Testing

Provides mock objects and data generation for testing:
- Mock component implementations
- Test data factories
- Mock event bus and managers
- Data generators for various scenarios
"""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QTableWidget
from PyQt6.QtCore import QObject, pyqtSignal


class MockDataType(Enum):
    """Types of mock data"""
    VIDEO_DATA = "video_data"
    USER_DATA = "user_data"
    DOWNLOAD_DATA = "download_data"
    PLATFORM_DATA = "platform_data"
    ERROR_DATA = "error_data"


@dataclass
class MockVideoData:
    """Mock video data structure"""
    id: str
    title: str
    url: str
    platform: str
    duration: int
    view_count: int
    upload_date: datetime
    thumbnail_url: str
    description: str = ""
    tags: List[str] = None


class MockComponent(QWidget):
    """Mock UI component for testing"""
    
    # Mock signals
    data_changed = pyqtSignal(dict)
    action_triggered = pyqtSignal(str)
    state_updated = pyqtSignal(str, object)
    
    def __init__(self, component_type: str = "generic"):
        super().__init__()
        self.component_type = component_type
        self._mock_data = {}
        self._mock_state = "initialized"
        self._event_log = []
        
    def set_mock_data(self, data: Dict[str, Any]):
        """Set mock data for the component"""
        self._mock_data = data
        self.data_changed.emit(data)
        self._log_event("data_set", data)
    
    def get_mock_data(self) -> Dict[str, Any]:
        """Get current mock data"""
        return self._mock_data.copy()
    
    def trigger_mock_action(self, action: str, params: Any = None):
        """Trigger a mock action"""
        self.action_triggered.emit(action)
        self._log_event("action_triggered", {"action": action, "params": params})
    
    def set_mock_state(self, state: str):
        """Set mock component state"""
        old_state = self._mock_state
        self._mock_state = state
        self.state_updated.emit(state, {"old": old_state, "new": state})
        self._log_event("state_changed", {"from": old_state, "to": state})
    
    def get_mock_state(self) -> str:
        """Get current mock state"""
        return self._mock_state
    
    def get_event_log(self) -> List[Dict[str, Any]]:
        """Get event log for verification"""
        return self._event_log.copy()
    
    def clear_event_log(self):
        """Clear event log"""
        self._event_log.clear()
    
    def _log_event(self, event_type: str, data: Any):
        """Log an event"""
        self._event_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        })


class MockDataGenerator:
    """Generator for various types of mock data"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
    
    def generate_video_data(self, count: int = 1) -> Union[MockVideoData, List[MockVideoData]]:
        """Generate mock video data"""
        platforms = ["youtube", "tiktok", "instagram", "twitter"]
        
        def create_video():
            video_id = self._random_string(11)
            title = self._random_title()
            platform = random.choice(platforms)
            
            return MockVideoData(
                id=video_id,
                title=title,
                url=f"https://{platform}.com/watch?v={video_id}",
                platform=platform,
                duration=random.randint(30, 3600),
                view_count=random.randint(100, 1000000),
                upload_date=self._random_date(),
                thumbnail_url=f"https://{platform}.com/thumb/{video_id}.jpg",
                description=self._random_description(),
                tags=self._random_tags()
            )
        
        videos = [create_video() for _ in range(count)]
        return videos[0] if count == 1 else videos
    
    def generate_user_data(self, count: int = 1) -> Union[Dict, List[Dict]]:
        """Generate mock user data"""
        def create_user():
            return {
                "id": self._random_string(8),
                "username": self._random_username(),
                "email": self._random_email(),
                "join_date": self._random_date(),
                "download_count": random.randint(0, 500),
                "favorite_platforms": random.sample(["youtube", "tiktok", "instagram"], 2),
                "settings": {
                    "quality_preference": random.choice(["720p", "1080p", "best"]),
                    "auto_download": random.choice([True, False]),
                    "theme": random.choice(["light", "dark"])
                }
            }
        
        users = [create_user() for _ in range(count)]
        return users[0] if count == 1 else users
    
    def generate_download_data(self, count: int = 1) -> Union[Dict, List[Dict]]:
        """Generate mock download data"""
        statuses = ["pending", "downloading", "completed", "failed", "paused"]
        
        def create_download():
            status = random.choice(statuses)
            total_size = random.randint(1024 * 1024, 500 * 1024 * 1024)  # 1MB to 500MB
            
            return {
                "id": self._random_string(12),
                "video_id": self._random_string(11),
                "url": f"https://example.com/video/{self._random_string(11)}",
                "title": self._random_title(),
                "status": status,
                "progress": random.randint(0, 100) if status in ["downloading", "completed"] else 0,
                "speed": random.randint(100, 5000) if status == "downloading" else 0,
                "total_size": total_size,
                "downloaded_size": int(total_size * (random.randint(0, 100) / 100)),
                "quality": random.choice(["720p", "1080p", "480p"]),
                "format": random.choice(["mp4", "webm", "mkv"]),
                "start_time": self._random_recent_date(),
                "estimated_completion": self._random_future_date()
            }
        
        downloads = [create_download() for _ in range(count)]
        return downloads[0] if count == 1 else downloads
    
    def generate_error_data(self, count: int = 1) -> Union[Dict, List[Dict]]:
        """Generate mock error data"""
        error_types = ["network", "parsing", "permission", "storage", "platform"]
        severities = ["low", "medium", "high", "critical"]
        
        def create_error():
            error_type = random.choice(error_types)
            return {
                "id": self._random_string(8),
                "type": error_type,
                "message": self._random_error_message(error_type),
                "severity": random.choice(severities),
                "timestamp": self._random_recent_date(),
                "component": random.choice(["downloader", "parser", "ui", "storage"]),
                "stack_trace": self._random_stack_trace(),
                "context": {
                    "url": f"https://example.com/video/{self._random_string(11)}",
                    "user_action": random.choice(["download", "parse", "preview"]),
                    "retry_count": random.randint(0, 3)
                }
            }
        
        errors = [create_error() for _ in range(count)]
        return errors[0] if count == 1 else errors
    
    # Helper methods
    def _random_string(self, length: int) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def _random_title(self) -> str:
        adjectives = ["Amazing", "Incredible", "Funny", "Epic", "Cool", "Awesome"]
        nouns = ["Video", "Tutorial", "Review", "Compilation", "Reaction", "Guide"]
        return f"{random.choice(adjectives)} {random.choice(nouns)} #{random.randint(1, 100)}"
    
    def _random_username(self) -> str:
        return f"user_{self._random_string(6)}"
    
    def _random_email(self) -> str:
        username = self._random_username()
        domains = ["gmail.com", "yahoo.com", "outlook.com", "example.com"]
        return f"{username}@{random.choice(domains)}"
    
    def _random_description(self) -> str:
        templates = [
            "This is an amazing video about {topic}. Don't forget to like and subscribe!",
            "In this video, we explore {topic} in detail. Hope you enjoy!",
            "A comprehensive guide to {topic}. Let me know what you think in the comments!",
            "Quick tutorial on {topic}. Follow along and learn something new!"
        ]
        topics = ["technology", "gaming", "music", "cooking", "travel", "education"]
        return random.choice(templates).format(topic=random.choice(topics))
    
    def _random_tags(self) -> List[str]:
        all_tags = ["tutorial", "review", "funny", "education", "gaming", "music", 
                   "technology", "diy", "cooking", "travel", "vlog", "reaction"]
        return random.sample(all_tags, random.randint(2, 5))
    
    def _random_date(self) -> datetime:
        start = datetime.now() - timedelta(days=365)
        end = datetime.now()
        return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))
    
    def _random_recent_date(self) -> datetime:
        return datetime.now() - timedelta(hours=random.randint(0, 24))
    
    def _random_future_date(self) -> datetime:
        return datetime.now() + timedelta(minutes=random.randint(1, 60))
    
    def _random_error_message(self, error_type: str) -> str:
        messages = {
            "network": ["Connection timeout", "Network unreachable", "DNS resolution failed"],
            "parsing": ["Invalid URL format", "Unsupported platform", "Failed to extract video info"],
            "permission": ["Access denied", "Insufficient permissions", "File locked"],
            "storage": ["Disk full", "Invalid file path", "Write permission denied"],
            "platform": ["Video not available", "Private video", "Age-restricted content"]
        }
        return random.choice(messages.get(error_type, ["Unknown error"]))
    
    def _random_stack_trace(self) -> str:
        return f"Traceback (most recent call last):\n  File 'test.py', line {random.randint(10, 100)}, in test_function\n    {self._random_error_message('network')}"


class TestDataFactory:
    """Factory for creating test data sets"""
    
    def __init__(self):
        self.generator = MockDataGenerator()
    
    def create_video_dataset(self, scenario: str) -> List[MockVideoData]:
        """Create video dataset for specific test scenarios"""
        if scenario == "empty":
            return []
        elif scenario == "single":
            return [self.generator.generate_video_data()]
        elif scenario == "small":
            return self.generator.generate_video_data(5)
        elif scenario == "medium":
            return self.generator.generate_video_data(50)
        elif scenario == "large":
            return self.generator.generate_video_data(500)
        elif scenario == "mixed_platforms":
            videos = []
            for platform in ["youtube", "tiktok", "instagram", "twitter"]:
                video = self.generator.generate_video_data()
                video.platform = platform
                videos.append(video)
            return videos
        else:
            return self.generator.generate_video_data(10)
    
    def create_error_scenario(self, scenario: str) -> List[Dict]:
        """Create error scenarios for testing"""
        if scenario == "network_issues":
            return [self.generator.generate_error_data() for _ in range(3)]
        elif scenario == "mixed_errors":
            return self.generator.generate_error_data(10)
        elif scenario == "critical_errors":
            errors = self.generator.generate_error_data(5)
            for error in errors:
                error["severity"] = "critical"
            return errors
        else:
            return []


class MockEventBus(QObject):
    """Mock event bus for testing"""
    
    # Signals for different event types
    component_registered = pyqtSignal(str, object)
    component_unregistered = pyqtSignal(str)
    data_updated = pyqtSignal(str, dict)
    state_changed = pyqtSignal(str, str, str)
    error_occurred = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self._subscribers = {}
        self._event_history = []
        self.enabled = True
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to events"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from events"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass
    
    def emit_event(self, event_type: str, data: Any = None):
        """Emit an event"""
        if not self.enabled:
            return
        
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        self._event_history.append(event)
        
        # Notify subscribers
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in event callback: {e}")
    
    def get_event_history(self) -> List[Dict]:
        """Get event history"""
        return self._event_history.copy()
    
    def clear_history(self):
        """Clear event history"""
        self._event_history.clear()
    
    def disable(self):
        """Disable event bus"""
        self.enabled = False
    
    def enable(self):
        """Enable event bus"""
        self.enabled = True


class MockThemeManager:
    """Mock theme manager for testing"""
    
    def __init__(self):
        self.current_theme = "light"
        self.available_themes = ["light", "dark", "high_contrast"]
        self._theme_data = {
            "light": {"background": "#ffffff", "text": "#000000"},
            "dark": {"background": "#2b2b2b", "text": "#ffffff"},
            "high_contrast": {"background": "#000000", "text": "#ffff00"}
        }
        self.change_callbacks = []
    
    def get_current_theme(self) -> str:
        """Get current theme name"""
        return self.current_theme
    
    def set_theme(self, theme_name: str):
        """Set current theme"""
        if theme_name in self.available_themes:
            old_theme = self.current_theme
            self.current_theme = theme_name
            
            # Notify callbacks
            for callback in self.change_callbacks:
                callback(old_theme, theme_name)
    
    def get_theme_data(self, theme_name: str = None) -> Dict[str, str]:
        """Get theme data"""
        theme = theme_name or self.current_theme
        return self._theme_data.get(theme, {}).copy()
    
    def add_change_callback(self, callback: Callable):
        """Add theme change callback"""
        self.change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable):
        """Remove theme change callback"""
        try:
            self.change_callbacks.remove(callback)
        except ValueError:
            pass


# =============================================================================
# Convenience Functions
# =============================================================================

def create_mock_component(component_type: str = "generic", **kwargs) -> MockComponent:
    """Create a mock component with initial data"""
    component = MockComponent(component_type)
    if kwargs:
        component.set_mock_data(kwargs)
    return component

def create_test_dataset(data_type: MockDataType, scenario: str = "default") -> Any:
    """Create a test dataset for specified type and scenario"""
    factory = TestDataFactory()
    
    if data_type == MockDataType.VIDEO_DATA:
        return factory.create_video_dataset(scenario)
    elif data_type == MockDataType.ERROR_DATA:
        return factory.create_error_scenario(scenario)
    else:
        generator = MockDataGenerator()
        if data_type == MockDataType.USER_DATA:
            return generator.generate_user_data(10)
        elif data_type == MockDataType.DOWNLOAD_DATA:
            return generator.generate_download_data(10)
        else:
            return []

def setup_mock_environment() -> Dict[str, Any]:
    """Setup a complete mock environment for testing"""
    return {
        "event_bus": MockEventBus(),
        "theme_manager": MockThemeManager(),
        "data_generator": MockDataGenerator(),
        "data_factory": TestDataFactory()
    } 