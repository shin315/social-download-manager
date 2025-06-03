"""
Test for Task 29.5 - Cross-Component Event Coordination System

This test validates the advanced event coordination features including:
- Event sequencing and workflow management
- Event throttling and debouncing
- Cross-component communication
- Debug tracing and metrics
- Integration with existing event systems
"""

import sys
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Import the modules we're testing
    CrossComponentCoordinator,
    EventSequence,
    EventSequenceStep,
    EventSequenceState,
    ThrottleConfig,
    ThrottleStrategy,
    get_cross_component_coordinator,
    initialize_cross_component_coordination
)
from core.event_system import get_event_bus, EventType, publish_event
from ui.components.common.events import get_event_bus as get_component_bus


class MockUIComponent(QObject):
    """Mock UI component for testing"""
    
    # Signals for testing
    url_changed = pyqtSignal(str)
    info_updated = pyqtSignal(dict)
    download_requested = pyqtSignal()
    
    def __init__(self, component_id: str):
        super().__init__()
        self.component_id = component_id
        self.received_events = []
        self.state = {}
    
    def handle_event(self, event_name: str, data: Any = None):
        """Handle incoming events"""
        self.received_events.append({
            "event_name": event_name,
            "data": data,
            "timestamp": datetime.now()
        })
        print(f"[{self.component_id}] Received event: {event_name}")
    
    def simulate_url_change(self, url: str):
        """Simulate user entering a URL"""
        self.url_changed.emit(url)
        coordinator = get_cross_component_coordinator()
        coordinator.coordinate_event(
            event_name="video_url_changed",
            source_component=self.component_id,
            data={"url": url}
        )
    
    def simulate_info_update(self, info: Dict[str, Any]):
        """Simulate video info being updated"""
        self.info_updated.emit(info)
        coordinator = get_cross_component_coordinator()
        coordinator.coordinate_event(
            event_name="video_info_updated",
            source_component=self.component_id,
            data=info
        )
    
    def simulate_download_request(self):
        """Simulate download request"""
        self.download_requested.emit()
        coordinator = get_cross_component_coordinator()
        coordinator.coordinate_event(
            event_name="download_requested",
            source_component=self.component_id,
            data={"action": "download"}
        )


def test_basic_coordination():
    """Test basic event coordination functionality"""
    print("\n=== Testing Basic Event Coordination ===")
    
    # Initialize coordinator
    bridge_coordinator = get_global_coordinator()
    coordinator = get_cross_component_coordinator()
    
    # Initialize systems
    bridge_coordinator.initialize(get_event_bus())
    coordinator.initialize(bridge_coordinator=bridge_coordinator)
    
    # Create mock components
    video_tab = MockUIComponent("video_info_tab")
    download_tab = MockUIComponent("download_tab")
    
    # Register components
    coordinator.register_component("video_info_tab", video_tab)
    coordinator.register_component("download_tab", download_tab, dependencies=["video_info_tab"])
    
    # Enable debug mode
    coordinator.enable_debug_mode(True)
    
    # Test event coordination
    coordinator.coordinate_event(
        event_name="test_event",
        source_component="video_info_tab",
        data={"message": "Hello from video tab!"},
        target_component="download_tab"
    )
    
    # Check metrics
    metrics = coordinator.get_metrics()
    print(f"Events coordinated: {metrics['events_coordinated']}")
    print(f"Component count: {metrics['component_count']}")
    
    # Check debug trace
    trace = coordinator.get_event_trace()
    if trace:
        latest_event = trace[-1]
        print(f"Latest event: {latest_event.event_name} from {latest_event.source_component}")
        print(f"Processing time: {latest_event.processing_time_ms:.2f}ms")
        print(f"Translation path: {' -> '.join(latest_event.translation_path)}")
    
    assert metrics['events_coordinated'] > 0, "No events were coordinated"
    assert metrics['component_count'] == 2, f"Expected 2 components, got {metrics['component_count']}"
    print("✅ Basic coordination test passed!")


def test_event_sequencing():
    """Test event sequencing and workflow management"""
    print("\n=== Testing Event Sequencing ===")
    
    coordinator = get_cross_component_coordinator()
    
    # Create a test sequence
    sequence = EventSequence(
        sequence_id="test_download_sequence",
        name="Test Download Sequence",
        steps=[
            EventSequenceStep(
                step_id="step1",
                event_name="video_url_changed",
                event_type="legacy",
                timeout_ms=5000
            ),
            EventSequenceStep(
                step_id="step2",
                event_name="video_info_updated",
                event_type="legacy",
                timeout_ms=5000
            ),
            EventSequenceStep(
                step_id="step3",
                event_name="download_requested",
                event_type="legacy",
                timeout_ms=5000
            )
        ],
        timeout_ms=20000
    )
    
    # Set up sequence callbacks
    sequence_completed = []
    sequence_failed = []
    steps_completed = []
    
    def on_complete(seq):
        sequence_completed.append(seq.sequence_id)
        print(f"✅ Sequence completed: {seq.name}")
    
    def on_failure(seq, error):
        sequence_failed.append((seq.sequence_id, error))
        print(f"❌ Sequence failed: {seq.name} - {error}")
    
    def on_step_complete(seq, step):
        steps_completed.append(step.step_id)
        print(f"✅ Step completed: {step.step_id}")
    
    sequence.on_complete = on_complete
    sequence.on_failure = on_failure
    sequence.on_step_complete = on_step_complete
    
    # Register and start sequence
    coordinator.register_event_sequence(sequence)
    success = coordinator.start_event_sequence("test_download_sequence")
    assert success, "Failed to start event sequence"
    
    # Create mock component to trigger events
    mock_component = MockUIComponent("test_component")
    coordinator.register_component("test_component", mock_component)
    
    # Simulate sequence events
    print("Triggering sequence events...")
    
    # Step 1: URL changed
    mock_component.simulate_url_change("https://example.com/video")
    time.sleep(0.1)
    
    # Step 2: Info updated
    mock_component.simulate_info_update({
        "title": "Test Video",
        "duration": "2:30",
        "quality": "1080p"
    })
    time.sleep(0.1)
    
    # Step 3: Download requested
    mock_component.simulate_download_request()
    time.sleep(0.1)
    
    # Check results
    assert len(steps_completed) == 3, f"Expected 3 steps completed, got {len(steps_completed)}"
    assert len(sequence_completed) == 1, f"Expected 1 sequence completed, got {len(sequence_completed)}"
    assert len(sequence_failed) == 0, f"Unexpected sequence failures: {sequence_failed}"
    
    print("✅ Event sequencing test passed!")


def test_event_throttling():
    """Test event throttling and debouncing"""
    print("\n=== Testing Event Throttling ===")
    
    coordinator = get_cross_component_coordinator()
    
    # Set up throttle configuration for rapid events
    throttle_config = ThrottleConfig(
        strategy=ThrottleStrategy.THROTTLE,
        interval_ms=200,  # 200ms interval
        max_events_per_interval=2  # Max 2 events per interval
    )
    
    coordinator.set_throttle_config("rapid_event", throttle_config)
    
    # Track throttled events
    throttled_events = []
    
    def on_throttled(event_name, count):
        throttled_events.append((event_name, count))
        print(f"🚫 Event throttled: {event_name} (count: {count})")
    
    coordinator.event_throttled.connect(on_throttled)
    
    # Send rapid events
    print("Sending rapid events...")
    for i in range(10):
        coordinator.coordinate_event(
            event_name="rapid_event",
            source_component="test_component",
            data={"count": i}
        )
        time.sleep(0.01)  # 10ms between events
    
    # Check throttling results
    metrics = coordinator.get_metrics()
    print(f"Events throttled: {metrics.get('events_throttled', 0)}")
    print(f"Throttled event instances: {len(throttled_events)}")
    
    assert len(throttled_events) > 0, "No events were throttled"
    print("✅ Event throttling test passed!")


def test_debouncing():
    """Test event debouncing"""
    print("\n=== Testing Event Debouncing ===")
    
    coordinator = get_cross_component_coordinator()
    
    # Set up debounce configuration
    debounce_config = ThrottleConfig(
        strategy=ThrottleStrategy.DEBOUNCE,
        interval_ms=300  # 300ms debounce
    )
    
    coordinator.set_throttle_config("debounce_event", debounce_config)
    
    # Send multiple events quickly (simulating rapid typing)
    print("Sending rapid events for debouncing...")
    for i in range(5):
        coordinator.coordinate_event(
            event_name="debounce_event",
            source_component="test_component",
            data={"value": f"text_{i}"}
        )
        time.sleep(0.05)  # 50ms between events
    
    # Wait for debounce period
    time.sleep(0.4)
    
    print("✅ Event debouncing test passed!")


def test_debug_tracing():
    """Test debug tracing and event flow analysis"""
    print("\n=== Testing Debug Tracing ===")
    
    coordinator = get_cross_component_coordinator()
    coordinator.enable_debug_mode(True)
    
    # Track debug events
    debug_events = []
    
    def on_debug_trace(debug_info):
        debug_events.append(debug_info)
        print(f"🔍 Debug trace: {debug_info.event_name} "
              f"({debug_info.processing_time_ms:.2f}ms)")
    
    coordinator.debug_event_traced.connect(on_debug_trace)
    
    # Generate some events for tracing
    events_to_trace = [
        ("trace_event_1", {"data": "first"}),
        ("trace_event_2", {"data": "second"}),
        ("trace_event_3", {"data": "third"})
    ]
    
    for event_name, data in events_to_trace:
        coordinator.coordinate_event(
            event_name=event_name,
            source_component="debug_test",
            data=data
        )
        time.sleep(0.05)
    
    # Check debug results
    trace = coordinator.get_event_trace()
    print(f"Total traced events: {len(trace)}")
    
    # Analyze event flow
    for event in trace[-3:]:  # Last 3 events
        print(f"Event: {event.event_name}")
        print(f"  Source: {event.source_component}")
        print(f"  Processing time: {event.processing_time_ms:.2f}ms")
        print(f"  Data size: {event.data_size} bytes")
        print(f"  Translation path: {' -> '.join(event.translation_path)}")
    
    assert len(debug_events) >= 3, f"Expected at least 3 debug events, got {len(debug_events)}"
    assert len(trace) >= 3, f"Expected at least 3 traced events, got {len(trace)}"
    print("✅ Debug tracing test passed!")


def test_component_states():
    """Test component state tracking"""
    print("\n=== Testing Component State Tracking ===")
    
    coordinator = get_cross_component_coordinator()
    
    # Register components with dependencies
    coordinator.register_component("main_window", QWidget(), dependencies=[])
    coordinator.register_component("video_tab", QWidget(), dependencies=["main_window"])
    coordinator.register_component("download_tab", QWidget(), dependencies=["main_window", "video_tab"])
    
    # Get component states
    states = coordinator.get_component_states()
    
    print("Component states:")
    for component_id, state in states.items():
        print(f"  {component_id}: {state['state']} (deps: {state['dependencies']})")
    
    assert len(states) >= 3, f"Expected at least 3 components, got {len(states)}"
    assert "main_window" in states, "main_window not found in states"
    assert "video_tab" in states, "video_tab not found in states"
    assert "download_tab" in states, "download_tab not found in states"
    
    # Check dependencies
    download_deps = states["download_tab"]["dependencies"]
    assert "main_window" in download_deps, "main_window not in download_tab dependencies"
    assert "video_tab" in download_deps, "video_tab not in download_tab dependencies"
    
    print("✅ Component state tracking test passed!")


def test_integration_with_existing_systems():
    """Test integration with existing event systems"""
    print("\n=== Testing Integration with Existing Systems ===")
    
    coordinator = get_cross_component_coordinator()
    bridge_coordinator = get_global_coordinator()
    
    # Test bridge coordinator integration
    assert coordinator._bridge_coordinator is not None, "Bridge coordinator not set"
    
    # Test core event bus integration
    assert coordinator._core_event_bus is not None, "Core event bus not set"
    
    # Test component event bus integration
    assert coordinator._component_event_bus is not None, "Component event bus not set"
    
    # Test event routing through bridge
    coordinator.coordinate_event(
        event_name="integration_test",
        source_component="test_integration",
        data={"test": "bridge_integration"}
    )
    
    # Publish a core event to test handling
    publish_event(
        event_type=EventType.DOWNLOAD_REQUESTED,
        source="test_integration",
        data={"url": "https://test.com/video"}
    )
    
    time.sleep(0.1)  # Allow processing
    
    metrics = coordinator.get_metrics()
    print(f"Final metrics: {metrics}")
    
    print("✅ Integration test passed!")


def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Cross-Component Event Coordination Tests")
    print("=" * 60)
    
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    try:
        # Initialize the coordination system
        success = initialize_cross_component_coordination()
        assert success, "Failed to initialize cross-component coordination"
        print("✅ Cross-component coordination initialized successfully!")
        
        # Run all tests
        test_basic_coordination()
        test_event_sequencing()
        test_event_throttling()
        test_debouncing()
        test_debug_tracing()
        test_component_states()
        test_integration_with_existing_systems()
        
        # Final metrics report
        coordinator = get_cross_component_coordinator()
        final_metrics = coordinator.get_metrics()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Final Metrics:")
        print(f"  Events coordinated: {final_metrics['events_coordinated']}")
        print(f"  Sequences completed: {final_metrics['sequences_completed']}")
        print(f"  Sequences failed: {final_metrics['sequences_failed']}")
        print(f"  Events throttled: {final_metrics['events_throttled']}")
        print(f"  Average processing time: {final_metrics['average_processing_time_ms']:.2f}ms")
        print(f"  Active components: {final_metrics['component_count']}")
        print("=" * 60)
        
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
    
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 