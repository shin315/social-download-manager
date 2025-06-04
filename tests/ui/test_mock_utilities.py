"""
Mock Utilities and Test Helpers for V2.0 UI Testing

Comprehensive collection of mock objects, test fixtures, and utility functions
to support testing of the V2.0 UI system components.
"""

import pytest
import tempfile
import time
import json
import os
import sys
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication, QWidget

# Add the UI components to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'components', 'core'))

from tab_lifecycle_manager import TabState, TabPriority
from component_bus import MessageType, Priority, DeliveryMode
from theme_manager import ThemeVariant


@dataclass
class MockTabData:
    """Mock tab data for testing"""
    id: str
    title: str = "Mock Tab"
    state: TabState = TabState.ACTIVE
    priority: TabPriority = TabPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)


@dataclass
class MockMessage:
    """Mock message for testing component bus"""
    message_type: MessageType
    sender_id: str
    channel: str
    event_type: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.IMMEDIATE
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class MockTabLifecycleManager(QObject):
    """Mock TabLifecycleManager for testing"""
    
    tab_created = pyqtSignal(str, dict)
    tab_activated = pyqtSignal(str)
    tab_hibernated = pyqtSignal(str, dict)
    tab_restored = pyqtSignal(str, dict)
    tab_destroyed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.tabs: Dict[str, MockTabData] = {}
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self.hibernation_enabled = True
        self.hibernation_threshold = 300  # 5 minutes
        
        # Mock performance metrics
        self.performance_metrics = {
            'tab_creation_time_avg': 2.5,
            'hibernation_time_avg': 25.0,
            'memory_usage_mb': 150.0
        }
    
    def create_tab(self, tab_id: str, priority: TabPriority = TabPriority.NORMAL) -> bool:
        """Create a mock tab"""
        if tab_id in self.tabs:
            return False
        
        tab_data = MockTabData(id=tab_id, priority=priority, state=TabState.INITIALIZING)
        self.tabs[tab_id] = tab_data
        
        # Simulate async initialization
        QTimer.singleShot(10, lambda: self._complete_tab_creation(tab_id))
        return True
    
    def _complete_tab_creation(self, tab_id: str):
        """Complete tab creation (simulated async)"""
        if tab_id in self.tabs:
            self.tabs[tab_id].state = TabState.BACKGROUND
            self.tab_created.emit(tab_id, self.tabs[tab_id].data)
    
    def activate_tab(self, tab_id: str) -> bool:
        """Activate a mock tab"""
        if tab_id not in self.tabs:
            return False
        
        self.tabs[tab_id].state = TabState.ACTIVE
        self.tabs[tab_id].last_accessed = time.time()
        self.tab_activated.emit(tab_id)
        return True
    
    def hibernate_tab(self, tab_id: str) -> bool:
        """Hibernate a mock tab"""
        if tab_id not in self.tabs:
            return False
        
        tab = self.tabs[tab_id]
        if tab.state == TabState.HIBERNATED:
            return True
        
        # Save snapshot
        self.snapshots[tab_id] = tab.data.copy()
        tab.state = TabState.HIBERNATED
        self.tab_hibernated.emit(tab_id, tab.data)
        return True
    
    def restore_tab(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """Restore a mock tab from hibernation"""
        if tab_id not in self.tabs:
            return None
        
        tab = self.tabs[tab_id]
        if tab.state != TabState.HIBERNATED:
            return tab.data
        
        # Restore from snapshot
        if tab_id in self.snapshots:
            tab.data = self.snapshots[tab_id].copy()
        
        tab.state = TabState.ACTIVE
        tab.last_accessed = time.time()
        self.tab_restored.emit(tab_id, tab.data)
        return tab.data
    
    def destroy_tab(self, tab_id: str) -> bool:
        """Destroy a mock tab"""
        if tab_id not in self.tabs:
            return False
        
        self.tabs[tab_id].state = TabState.TERMINATED
        self.tab_destroyed.emit(tab_id)
        del self.tabs[tab_id]
        
        if tab_id in self.snapshots:
            del self.snapshots[tab_id]
        
        return True
    
    def get_tab_state(self, tab_id: str) -> Optional[TabState]:
        """Get tab state"""
        return self.tabs.get(tab_id, MockTabData("")).state if tab_id in self.tabs else None
    
    def get_tab_data(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """Get tab data"""
        return self.tabs.get(tab_id, MockTabData("")).data if tab_id in self.tabs else None
    
    def update_tab_state(self, tab_id: str, state_data: Dict[str, Any]) -> bool:
        """Update tab state data"""
        if tab_id not in self.tabs:
            return False
        
        self.tabs[tab_id].data.update(state_data)
        return True
    
    def get_active_tabs(self) -> List[str]:
        """Get list of active tab IDs"""
        return [tab_id for tab_id, tab in self.tabs.items() 
                if tab.state == TabState.ACTIVE]
    
    def get_hibernated_tabs(self) -> List[str]:
        """Get list of hibernated tab IDs"""
        return [tab_id for tab_id, tab in self.tabs.items() 
                if tab.state == TabState.HIBERNATED]
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get mock performance metrics"""
        return self.performance_metrics.copy()
    
    def shutdown(self):
        """Shutdown mock manager"""
        for tab_id in list(self.tabs.keys()):
            self.destroy_tab(tab_id)


class MockComponentBus(QObject):
    """Mock ComponentBus for testing"""
    
    message_sent = pyqtSignal(dict)
    message_received = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.subscribers: Dict[str, Dict[str, Callable]] = {}
        self.message_queue: List[MockMessage] = []
        self.components: Dict[str, Dict[str, Any]] = {}
        self.hibernated_components: set = set()
        self.message_history: List[MockMessage] = []
        
        # Mock performance metrics
        self.metrics = {
            'messages_sent': 0,
            'messages_processed': 0,
            'avg_processing_time_ms': 0.1,
            'queue_size': 0
        }
    
    def subscribe(self, component_id: str, channel: str, callback: Callable):
        """Subscribe to messages"""
        if channel not in self.subscribers:
            self.subscribers[channel] = {}
        
        self.subscribers[channel][component_id] = callback
        
        # Register component
        if component_id not in self.components:
            self.components[component_id] = {
                'channels': [channel],
                'active': True,
                'hibernated': False
            }
        else:
            if channel not in self.components[component_id]['channels']:
                self.components[component_id]['channels'].append(channel)
    
    def unsubscribe(self, component_id: str, channel: str):
        """Unsubscribe from messages"""
        if channel in self.subscribers and component_id in self.subscribers[channel]:
            del self.subscribers[channel][component_id]
            
            if component_id in self.components:
                if channel in self.components[component_id]['channels']:
                    self.components[component_id]['channels'].remove(channel)
    
    def send_event(self, sender_id: str, channel: str, event_type: str, 
                   payload: Dict[str, Any], priority: Priority = Priority.NORMAL):
        """Send an event message"""
        message = MockMessage(
            message_type=MessageType.EVENT,
            sender_id=sender_id,
            channel=channel,
            event_type=event_type,
            payload=payload,
            priority=priority
        )
        
        self._queue_message(message)
        self.metrics['messages_sent'] += 1
        self.message_sent.emit(message.__dict__)
    
    def send_request(self, sender_id: str, channel: str, request_type: str, 
                     payload: Dict[str, Any], timeout: float = 30.0) -> str:
        """Send a request message"""
        import uuid
        correlation_id = str(uuid.uuid4())
        
        message = MockMessage(
            message_type=MessageType.REQUEST,
            sender_id=sender_id,
            channel=channel,
            event_type=request_type,
            payload=payload,
            correlation_id=correlation_id
        )
        
        self._queue_message(message)
        self.metrics['messages_sent'] += 1
        self.message_sent.emit(message.__dict__)
        return correlation_id
    
    def send_response(self, sender_id: str, recipient_id: str, response_type: str,
                      payload: Dict[str, Any], correlation_id: str):
        """Send a response message"""
        message = MockMessage(
            message_type=MessageType.RESPONSE,
            sender_id=sender_id,
            channel="response",
            event_type=response_type,
            payload=payload,
            correlation_id=correlation_id
        )
        
        self._queue_message(message)
        self.metrics['messages_sent'] += 1
        self.message_sent.emit(message.__dict__)
    
    def send_broadcast(self, sender_id: str, channel: str, event_type: str,
                       payload: Dict[str, Any]):
        """Send a broadcast message"""
        message = MockMessage(
            message_type=MessageType.BROADCAST,
            sender_id=sender_id,
            channel=channel,
            event_type=event_type,
            payload=payload,
            delivery_mode=DeliveryMode.BROADCAST
        )
        
        self._queue_message(message)
        self.metrics['messages_sent'] += 1
        self.message_sent.emit(message.__dict__)
    
    def _queue_message(self, message: MockMessage):
        """Queue a message for processing"""
        self.message_queue.append(message)
        self.message_history.append(message)
        self.metrics['queue_size'] = len(self.message_queue)
    
    def process_messages(self):
        """Process queued messages"""
        # Sort by priority
        self.message_queue.sort(key=lambda m: m.priority.value, reverse=True)
        
        processed_count = 0
        start_time = time.perf_counter()
        
        while self.message_queue and processed_count < 50:  # Batch processing
            message = self.message_queue.pop(0)
            self._deliver_message(message)
            processed_count += 1
        
        processing_time = (time.perf_counter() - start_time) * 1000
        if processed_count > 0:
            self.metrics['avg_processing_time_ms'] = processing_time / processed_count
        
        self.metrics['messages_processed'] += processed_count
        self.metrics['queue_size'] = len(self.message_queue)
    
    def _deliver_message(self, message: MockMessage):
        """Deliver a message to subscribers"""
        if message.channel in self.subscribers:
            for component_id, callback in self.subscribers[message.channel].items():
                # Skip hibernated components (except for critical messages)
                if (component_id in self.hibernated_components and 
                    message.priority != Priority.CRITICAL):
                    continue
                
                try:
                    callback(message)
                    self.message_received.emit(message.__dict__)
                except Exception as e:
                    print(f"Error delivering message to {component_id}: {e}")
    
    def set_component_hibernated(self, component_id: str, hibernated: bool):
        """Set component hibernation state"""
        if hibernated:
            self.hibernated_components.add(component_id)
        else:
            self.hibernated_components.discard(component_id)
        
        if component_id in self.components:
            self.components[component_id]['hibernated'] = hibernated
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get bus metrics"""
        return self.metrics.copy()
    
    def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get message history"""
        recent_messages = self.message_history[-limit:] if limit else self.message_history
        return [msg.__dict__ for msg in recent_messages]
    
    def clear_message_history(self):
        """Clear message history"""
        self.message_history.clear()
    
    def stop(self):
        """Stop the mock bus"""
        self.message_queue.clear()
        self.subscribers.clear()
        self.components.clear()
        self.hibernated_components.clear()


class MockThemeManager(QObject):
    """Mock ThemeManager for testing"""
    
    theme_changed = pyqtSignal(str)
    token_updated = pyqtSignal(str, str, str)
    
    def __init__(self):
        super().__init__()
        self.current_variant = ThemeVariant.LIGHT
        self.theme_tokens = {
            ThemeVariant.LIGHT: {
                "colors": {
                    "primary": "#2563eb",
                    "background": "#ffffff",
                    "text": "#1e293b"
                },
                "fonts": {
                    "body": "Inter",
                    "heading": "Inter"
                },
                "spacing": {
                    "small": "8px",
                    "medium": "16px",
                    "large": "24px"
                }
            },
            ThemeVariant.DARK: {
                "colors": {
                    "primary": "#3b82f6",
                    "background": "#0f172a",
                    "text": "#f1f5f9"
                },
                "fonts": {
                    "body": "Inter",
                    "heading": "Inter"
                },
                "spacing": {
                    "small": "8px",
                    "medium": "16px",
                    "large": "24px"
                }
            }
        }
        self.component_overrides: Dict[str, Dict[str, Any]] = {}
        self.switch_count = 0
        self.switch_times: List[float] = []
    
    def switch_theme(self, variant: ThemeVariant) -> bool:
        """Switch to a theme variant"""
        if variant not in self.theme_tokens:
            return False
        
        start_time = time.perf_counter()
        
        old_variant = self.current_variant
        self.current_variant = variant
        self.switch_count += 1
        
        # Simulate theme switching delay
        time.sleep(0.001)  # 1ms delay
        
        switch_time = (time.perf_counter() - start_time) * 1000
        self.switch_times.append(switch_time)
        
        self.theme_changed.emit(variant.value)
        return True
    
    def get_token(self, category: str, token_name: str) -> Optional[str]:
        """Get a theme token value"""
        variant_tokens = self.theme_tokens.get(self.current_variant, {})
        category_tokens = variant_tokens.get(category, {})
        return category_tokens.get(token_name)
    
    def get_component_token(self, component_id: str, category: str, token_name: str) -> Optional[str]:
        """Get a component-specific theme token"""
        # Check for component override first
        if component_id in self.component_overrides:
            override = self.component_overrides[component_id]
            if category in override and token_name in override[category]:
                return override[category][token_name]
        
        # Fall back to regular token
        return self.get_token(category, token_name)
    
    def register_component_override(self, component_id: str, overrides: Dict[str, Any]):
        """Register component-specific theme overrides"""
        self.component_overrides[component_id] = overrides
    
    def get_all_tokens(self) -> Dict[str, Any]:
        """Get all tokens for current theme"""
        return self.theme_tokens.get(self.current_variant, {}).copy()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get theme performance metrics"""
        avg_switch_time = (sum(self.switch_times) / len(self.switch_times) 
                          if self.switch_times else 0.0)
        
        return {
            'switch_count': self.switch_count,
            'avg_switch_time_ms': avg_switch_time,
            'current_variant': self.current_variant.value,
            'registered_overrides': len(self.component_overrides)
        }
    
    def save_preferences(self) -> bool:
        """Mock save preferences"""
        return True
    
    def load_preferences(self) -> bool:
        """Mock load preferences"""
        return True
    
    def cleanup(self):
        """Cleanup mock theme manager"""
        self.component_overrides.clear()
        self.switch_times.clear()


class MockAppController(QObject):
    """Mock AppController for testing"""
    
    service_registered = pyqtSignal(str)
    global_state_changed = pyqtSignal(str, object, object)
    configuration_updated = pyqtSignal(dict)
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self.services: Dict[str, Any] = {}
        self.global_state: Dict[str, Any] = {}
        self.health_status = {'overall_health': 'healthy', 'service_health': {}}
        
        # Initialize mock services
        self._initialize_mock_services()
    
    def _initialize_mock_services(self):
        """Initialize mock services"""
        self.services = {
            'tab_lifecycle_manager': MockTabLifecycleManager(),
            'component_bus': MockComponentBus(),
            'theme_manager': MockThemeManager()
        }
        
        for service_name in self.services:
            self.service_registered.emit(service_name)
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service by name"""
        return self.services.get(service_name)
    
    def register_service(self, service_name: str, service_instance: Any, 
                        scope: str = "singleton", dependencies: Optional[List[str]] = None):
        """Register a service"""
        self.services[service_name] = service_instance
        self.service_registered.emit(service_name)
    
    def set_global_state(self, key: str, value: Any):
        """Set global state"""
        old_value = self.global_state.get(key)
        self.global_state[key] = value
        self.global_state_changed.emit(key, old_value, value)
    
    def get_global_state(self, key: str, default: Any = None) -> Any:
        """Get global state"""
        return self.global_state.get(key, default)
    
    def update_configuration(self, new_config: Dict[str, Any]):
        """Update configuration"""
        self.config.update(new_config)
        self.configuration_updated.emit(new_config)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status"""
        return self.health_status.copy()
    
    def start_monitoring(self):
        """Start health monitoring"""
        # Mock monitoring - just update health status
        for service_name in self.services:
            self.health_status['service_health'][service_name] = 'healthy'
    
    def shutdown(self):
        """Shutdown mock controller"""
        for service in self.services.values():
            if hasattr(service, 'shutdown'):
                service.shutdown()
            elif hasattr(service, 'stop'):
                service.stop()
            elif hasattr(service, 'cleanup'):
                service.cleanup()
        
        self.services.clear()
        self.global_state.clear()


class TestConfiguration:
    """Test configuration helper"""
    
    @staticmethod
    def create_temp_config(temp_dir: str, custom_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create temporary configuration for testing"""
        base_config = {
            'state_dir': temp_dir,
            'enable_performance_monitoring': True,
            'enable_hibernation': True,
            'hibernation_threshold': 60,  # 1 minute for testing
            'enable_component_bus': True,
            'message_processing_interval': 10,  # 10ms for testing
            'enable_theme_management': True,
            'theme_config_dir': temp_dir,
            'max_hibernated_tabs': 10,
            'snapshot_interval': 30,  # 30 seconds for testing
            'log_level': 'DEBUG'
        }
        
        if custom_options:
            base_config.update(custom_options)
        
        return base_config
    
    @staticmethod
    def create_test_directories(base_dir: str) -> Dict[str, str]:
        """Create test directory structure"""
        directories = {
            'state': os.path.join(base_dir, 'state'),
            'themes': os.path.join(base_dir, 'themes'),
            'snapshots': os.path.join(base_dir, 'snapshots'),
            'logs': os.path.join(base_dir, 'logs')
        }
        
        for dir_path in directories.values():
            os.makedirs(dir_path, exist_ok=True)
        
        return directories


class MockDataGenerator:
    """Generate mock data for testing"""
    
    @staticmethod
    def create_tab_data(count: int = 10) -> List[MockTabData]:
        """Generate mock tab data"""
        tabs = []
        for i in range(count):
            tab = MockTabData(
                id=f"tab_{i}",
                title=f"Mock Tab {i}",
                state=TabState.ACTIVE if i % 3 == 0 else TabState.BACKGROUND,
                priority=TabPriority.HIGH if i % 5 == 0 else TabPriority.NORMAL,
                data={
                    'url': f'https://example.com/page{i}',
                    'scroll_position': i * 100,
                    'form_data': {'field1': f'value{i}', 'field2': f'data{i}'}
                }
            )
            tabs.append(tab)
        return tabs
    
    @staticmethod
    def create_messages(count: int = 50) -> List[MockMessage]:
        """Generate mock messages"""
        messages = []
        message_types = [MessageType.EVENT, MessageType.REQUEST, MessageType.BROADCAST]
        priorities = [Priority.LOW, Priority.NORMAL, Priority.HIGH, Priority.CRITICAL]
        
        for i in range(count):
            message = MockMessage(
                message_type=message_types[i % len(message_types)],
                sender_id=f"component_{i % 5}",
                channel=f"channel_{i % 3}",
                event_type=f"event_{i}",
                payload={'index': i, 'data': f'test_data_{i}'},
                priority=priorities[i % len(priorities)]
            )
            messages.append(message)
        
        return messages
    
    @staticmethod
    def create_performance_data() -> Dict[str, Any]:
        """Generate mock performance data"""
        return {
            'cpu_usage': 15.5,
            'memory_usage_mb': 125.8,
            'tab_count': 8,
            'active_tabs': 3,
            'hibernated_tabs': 5,
            'message_queue_size': 12,
            'avg_response_time_ms': 2.3,
            'theme_switch_count': 5,
            'error_count': 0
        }


class TestAssertion:
    """Custom assertion helpers for UI testing"""
    
    @staticmethod
    def assert_tab_state(tab_manager, tab_id: str, expected_state: TabState):
        """Assert tab is in expected state"""
        actual_state = tab_manager.get_tab_state(tab_id)
        assert actual_state == expected_state, \
            f"Tab {tab_id} expected to be in state {expected_state}, but was {actual_state}"
    
    @staticmethod
    def assert_message_received(bus, channel: str, event_type: str, timeout: float = 1.0):
        """Assert a message was received within timeout"""
        start_time = time.time()
        history = bus.get_message_history()
        
        while time.time() - start_time < timeout:
            for msg_dict in history:
                if msg_dict.get('channel') == channel and msg_dict.get('event_type') == event_type:
                    return True
            time.sleep(0.01)
            history = bus.get_message_history()
        
        assert False, f"Message {event_type} on channel {channel} not received within {timeout}s"
    
    @staticmethod
    def assert_performance_within_threshold(actual: float, threshold: float, metric_name: str):
        """Assert performance metric is within threshold"""
        assert actual <= threshold, \
            f"Performance metric {metric_name} ({actual}) exceeded threshold ({threshold})"
    
    @staticmethod
    def assert_theme_applied(theme_manager, expected_variant: ThemeVariant):
        """Assert theme variant is applied"""
        actual_variant = theme_manager.current_variant
        assert actual_variant == expected_variant, \
            f"Expected theme {expected_variant}, but got {actual_variant}"


# Pytest fixtures for common mock objects
@pytest.fixture
def mock_tab_manager():
    """Provide mock tab lifecycle manager"""
    return MockTabLifecycleManager()


@pytest.fixture
def mock_component_bus():
    """Provide mock component bus"""
    return MockComponentBus()


@pytest.fixture
def mock_theme_manager():
    """Provide mock theme manager"""
    return MockThemeManager()


@pytest.fixture
def mock_app_controller():
    """Provide mock app controller"""
    return MockAppController()


@pytest.fixture
def test_config(tmp_path):
    """Provide test configuration"""
    return TestConfiguration.create_temp_config(str(tmp_path))


@pytest.fixture
def test_directories(tmp_path):
    """Provide test directory structure"""
    return TestConfiguration.create_test_directories(str(tmp_path))


@pytest.fixture
def mock_tab_data():
    """Provide mock tab data"""
    return MockDataGenerator.create_tab_data(10)


@pytest.fixture
def mock_messages():
    """Provide mock messages"""
    return MockDataGenerator.create_messages(25)


@pytest.fixture
def qt_app():
    """Provide QApplication for tests"""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    yield app


if __name__ == "__main__":
    # Demo of mock utilities
    print("🧪 V2.0 UI Mock Utilities Demo")
    
    # Create mock objects
    tab_manager = MockTabLifecycleManager()
    bus = MockComponentBus()
    theme_manager = MockThemeManager()
    
    # Demo tab lifecycle
    print("\n📑 Tab Lifecycle Demo:")
    tab_manager.create_tab("demo_tab", TabPriority.HIGH)
    tab_manager.activate_tab("demo_tab")
    print(f"Tab state: {tab_manager.get_tab_state('demo_tab')}")
    
    # Demo messaging
    print("\n💌 Component Bus Demo:")
    def demo_handler(message):
        print(f"Received: {message.event_type}")
    
    bus.subscribe("demo_component", "demo_channel", demo_handler)
    bus.send_event("sender", "demo_channel", "demo_event", {"test": "data"})
    bus.process_messages()
    
    # Demo theme management
    print("\n🎨 Theme Manager Demo:")
    print(f"Current theme: {theme_manager.current_variant}")
    theme_manager.switch_theme(ThemeVariant.DARK)
    print(f"Switched to: {theme_manager.current_variant}")
    
    print("\n✅ Mock utilities demo completed!") 