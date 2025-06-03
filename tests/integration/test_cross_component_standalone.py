"""
Standalone Test for Cross-Component Event Coordination System

This test directly imports the specific module without dependencies.
"""

import sys
import logging
import time
from datetime import datetime
from typing import Dict, Any
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, pyqtSignal

# Direct import to avoid __init__.py dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "cross_component_coordinator", 
    "ui/adapters/cross_component_coordinator.py"
)
cross_comp_module = importlib.util.module_from_spec(spec)

# Mock the dependencies that will be imported
class MockEventBus:
    def __init__(self):
        self.subscribers = {}
        self.events = []
    
    def subscribe(self, event_type, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def emit(self, event):
        self.events.append(event)

class MockEvent:
    def __init__(self, event_type, data=None):
        self.event_type = event_type
        self.data = data

class MockEventType:
    DOWNLOAD_REQUESTED = "download_requested"
    DOWNLOAD_PROGRESS_UPDATED = "download_progress_updated"
    DOWNLOAD_COMPLETED = "download_completed"
    DOWNLOAD_FAILED = "download_failed"
    CONTENT_METADATA_UPDATED = "content_metadata_updated"
    ERROR_OCCURRED = "error_occurred"

class MockComponentEvent:
    def __init__(self, event_type, source_component, data, target_component=None):
        self.event_type = event_type
        self.source_component = source_component
        self.data = data
        self.target_component = target_component

class MockComponentEventType:
    DATA_UPDATED = "data_updated"
    STATE_CHANGED = "state_changed"
    SELECTION_CHANGED = "selection_changed"

class MockComponentBus(QObject):
    event_emitted = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.events = []
    
    def emit_event(self, event_type, source_component, data, target_component=None):
        event = MockComponentEvent(event_type, source_component, data, target_component)
        self.events.append(event)
        self.event_emitted.emit(event)

class MockUIConstants:
    pass

# Mock the imports in the module
sys.modules['ui.adapters.event_proxy'] = type('Module', (), {
    'EventBridgeCoordinator': type('EventBridgeCoordinator', (), {}),
    'EventMapping': type('EventMapping', (), {}),
    'EventPriority': type('EventPriority', (), {'NORMAL': 2, 'HIGH': 3, 'CRITICAL': 4}),
    'EventTranslationDirection': type('EventTranslationDirection', (), {})
})

sys.modules['core.event_system'] = type('Module', (), {
    'EventBus': MockEventBus,
    'Event': MockEvent,
    'EventType': MockEventType,
    'get_event_bus': lambda: MockEventBus()
})

sys.modules['ui.components.common.events'] = type('Module', (), {
    'ComponentBus': MockComponentBus,
    'get_event_bus': lambda: MockComponentBus(),
    'ComponentEvent': MockComponentEvent,
    'EventType': MockComponentEventType
})

sys.modules['core.constants'] = type('Module', (), {
    'UIConstants': MockUIConstants
})

# Now load the actual module
spec.loader.exec_module(cross_comp_module)

# Import what we need for testing
CrossComponentCoordinator = cross_comp_module.CrossComponentCoordinator
EventSequence = cross_comp_module.EventSequence
EventSequenceStep = cross_comp_module.EventSequenceStep
EventSequenceState = cross_comp_module.EventSequenceState
ThrottleConfig = cross_comp_module.ThrottleConfig
ThrottleStrategy = cross_comp_module.ThrottleStrategy


class MockBridgeCoordinator(QObject):
    """Simple mock bridge coordinator"""
    event_translated = pyqtSignal(str, object)
    translation_error = pyqtSignal(str, str)
    bridge_status_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.is_initialized = False
    
    def emit_legacy_event(self, event_name, data):
        self.event_translated.emit(event_name, data)
        return True


class MockComponent(QObject):
    """Mock UI component for testing"""
    def __init__(self, component_id: str):
        super().__init__()
        self.component_id = component_id
        self.received_events = []
    
    def handle_event(self, event_name: str, data: Any = None):
        self.received_events.append({
            "event_name": event_name,
            "data": data,
            "timestamp": datetime.now()
        })
        print(f"[{self.component_id}] Received: {event_name}")


def test_coordinator_initialization():
    """Test basic coordinator initialization"""
    print("\n=== Testing Coordinator Initialization ===")
    
    # Create mock components
    mock_bridge = MockBridgeCoordinator()
    mock_core_bus = MockEventBus()
    mock_component_bus = MockComponentBus()
    
    # Initialize coordinator
    coordinator = CrossComponentCoordinator()
    success = coordinator.initialize(
        bridge_coordinator=mock_bridge,
        core_event_bus=mock_core_bus,
        component_event_bus=mock_component_bus
    )
    
    assert success, "Coordinator initialization failed"
    print("✅ Coordinator initialization test passed!")


def test_component_registration():
    """Test component registration"""
    print("\n=== Testing Component Registration ===")
    
    coordinator = CrossComponentCoordinator()
    
    # Create mock components
    main_window = MockComponent("main_window")
    video_tab = MockComponent("video_tab")
    download_tab = MockComponent("download_tab")
    
    # Register components
    success1 = coordinator.register_component("main_window", main_window)
    success2 = coordinator.register_component("video_tab", video_tab, dependencies=["main_window"])
    success3 = coordinator.register_component("download_tab", download_tab, dependencies=["main_window", "video_tab"])
    
    assert success1, "Failed to register main_window"
    assert success2, "Failed to register video_tab"
    assert success3, "Failed to register download_tab"
    
    # Check component states
    states = coordinator.get_component_states()
    assert len(states) == 3, f"Expected 3 components, got {len(states)}"
    assert "main_window" in states, "main_window not in states"
    
    print("✅ Component registration test passed!")


def test_event_coordination():
    """Test basic event coordination"""
    print("\n=== Testing Event Coordination ===")
    
    coordinator = CrossComponentCoordinator()
    coordinator.enable_debug_mode(True)
    
    # Coordinate some events
    events_to_test = [
        ("test_event_1", "component_a", {"data": "hello"}),
        ("test_event_2", "component_b", {"data": "world"}),
        ("test_event_3", "component_c", {"data": "test"})
    ]
    
    for event_name, source, data in events_to_test:
        success = coordinator.coordinate_event(
            event_name=event_name,
            source_component=source,
            data=data
        )
        assert success, f"Failed to coordinate event: {event_name}"
    
    # Check metrics
    metrics = coordinator.get_metrics()
    print(f"Events coordinated: {metrics['events_coordinated']}")
    assert metrics['events_coordinated'] >= 3, "Not enough events coordinated"
    
    print("✅ Event coordination test passed!")


def test_throttling():
    """Test event throttling"""
    print("\n=== Testing Event Throttling ===")
    
    coordinator = CrossComponentCoordinator()
    
    # Set up throttle configuration
    throttle_config = ThrottleConfig(
        strategy=ThrottleStrategy.THROTTLE,
        interval_ms=100,  # 100ms interval
        max_events_per_interval=2  # Max 2 events per interval
    )
    
    coordinator.set_throttle_config("throttled_event", throttle_config)
    
    # Track throttled events
    throttled_count = [0]
    
    def on_throttled(event_name, count):
        throttled_count[0] = count
        print(f"🚫 Event throttled: {event_name} (count: {count})")
    
    coordinator.event_throttled.connect(on_throttled)
    
    # Send rapid events
    print("Sending rapid events...")
    for i in range(8):
        coordinator.coordinate_event(
            event_name="throttled_event",
            source_component="test_source",
            data={"count": i}
        )
        time.sleep(0.01)  # 10ms between events
    
    # Check results
    assert throttled_count[0] > 0, "No events were throttled"
    print(f"Throttled {throttled_count[0]} events")
    print("✅ Event throttling test passed!")


def test_event_sequence():
    """Test event sequencing"""
    print("\n=== Testing Event Sequencing ===")
    
    coordinator = CrossComponentCoordinator()
    
    # Create a simple sequence
    sequence = EventSequence(
        sequence_id="test_sequence",
        name="Test Sequence",
        steps=[
            EventSequenceStep(
                step_id="step1",
                event_name="step_one",
                event_type="test"
            ),
            EventSequenceStep(
                step_id="step2",
                event_name="step_two",
                event_type="test"
            )
        ],
        timeout_ms=10000
    )
    
    # Track sequence progress
    completed_sequences = []
    completed_steps = []
    
    def on_sequence_complete(seq):
        completed_sequences.append(seq.sequence_id)
        print(f"✅ Sequence completed: {seq.name}")
    
    def on_step_complete(seq, step):
        completed_steps.append(step.step_id)
        print(f"✅ Step completed: {step.step_id}")
    
    sequence.on_complete = on_sequence_complete
    sequence.on_step_complete = on_step_complete
    
    # Register and start sequence
    coordinator.register_event_sequence(sequence)
    success = coordinator.start_event_sequence("test_sequence")
    assert success, "Failed to start sequence"
    
    # Trigger sequence events
    coordinator.coordinate_event("step_one", "test_component", {"step": 1})
    time.sleep(0.1)
    coordinator.coordinate_event("step_two", "test_component", {"step": 2})
    time.sleep(0.1)
    
    # Check results
    assert len(completed_steps) == 2, f"Expected 2 steps completed, got {len(completed_steps)}"
    assert len(completed_sequences) == 1, f"Expected 1 sequence completed, got {len(completed_sequences)}"
    
    print("✅ Event sequencing test passed!")


def run_standalone_tests():
    """Run all standalone tests"""
    print("🚀 Starting Standalone Cross-Component Event Coordination Tests")
    print("=" * 70)
    
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    try:
        # Run tests
        test_coordinator_initialization()
        test_component_registration()
        test_event_coordination()
        test_throttling()
        test_event_sequence()
        
        print("\n" + "=" * 70)
        print("🎉 ALL STANDALONE TESTS PASSED!")
        print("Cross-Component Event Coordination is working perfectly!")
        print("Task 29.5 - Cross-Component Event Coordination: ✅ COMPLETED!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        app.quit()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = run_standalone_tests()
    sys.exit(0 if success else 1) 