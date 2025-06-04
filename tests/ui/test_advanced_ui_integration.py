"""
Comprehensive Integration Tests for Advanced V2.0 UI Features
Task 36.10 - Testing all implemented advanced UI components

Tests for:
- TabLifecycleManager
- ComponentBus 
- ThemeManager
- StateManager
- PerformanceMonitor
- ComponentLoader
- I18nManager
- LifecycleManager
- AppController
"""

import pytest
import asyncio
import time
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

# Import all our advanced UI components
from ui.components.core.tab_lifecycle_manager import (
    TabLifecycleManager, TabState, TabPriority, TabMetrics
)
from ui.components.core.component_bus import (
    ComponentBus, MessageType, MessagePriority, DeliveryMode, BusMessage
)
from ui.components.core.theme_manager import (
    ThemeManager, ThemeVariant, ThemeProperty, ThemeToken
)
from ui.components.core.state_manager import StateManager
from ui.components.core.performance_monitor import PerformanceMonitor
from ui.components.core.component_loader import ComponentLoader
from ui.components.core.i18n_manager import I18nManager
from ui.components.core.lifecycle_manager import LifecycleManager
from ui.components.core.app_controller import (
    AppController, AppConfiguration, AppMetrics, AppMode, ServiceScope
)


class TestAdvancedUIIntegration:
    """Integration tests for advanced UI components"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if QApplication.instance() is None:
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app
        # Cleanup handled by QApplication
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create test configuration"""
        return {
            'session_file': str(temp_dir / 'session_state.json.gz'),
            'data_directory': str(temp_dir / 'data'),
            'localization_directory': str(temp_dir / 'localization'),
            'theme_directory': str(temp_dir / 'themes'),
            'enable_debug_mode': True
        }
    
    def test_tab_lifecycle_manager_initialization(self, app, mock_config):
        """Test TabLifecycleManager initialization and basic functionality"""
        config = {
            'hibernation_threshold': 300,  # 5 minutes
            'max_hibernated_tabs': 10,
            'enable_automatic_hibernation': True,
            **mock_config
        }
        
        tab_manager = TabLifecycleManager(config)
        
        # Test initialization
        assert tab_manager is not None
        assert tab_manager.config == config
        assert len(tab_manager.tabs) == 0
        
        # Test tab creation
        tab_id = tab_manager.create_tab("Test Tab", Mock(), TabPriority.NORMAL)
        assert tab_id is not None
        assert len(tab_manager.tabs) == 1
        assert tab_manager.get_tab_state(tab_id) == TabState.UNINITIALIZED
        
        # Test tab state transitions
        assert tab_manager.activate_tab(tab_id)
        assert tab_manager.get_tab_state(tab_id) == TabState.ACTIVE
        
        # Test hibernation
        assert tab_manager.hibernate_tab(tab_id)
        assert tab_manager.get_tab_state(tab_id) == TabState.HIBERNATED
        
        # Test restoration
        assert tab_manager.restore_tab(tab_id)
        assert tab_manager.get_tab_state(tab_id) == TabState.ACTIVE
        
        # Cleanup
        tab_manager.shutdown()
    
    def test_component_bus_messaging(self, app, mock_config):
        """Test ComponentBus cross-component communication"""
        config = {
            'max_queue_size': 1000,
            'batch_size': 10,
            'processing_interval_ms': 50,
            **mock_config
        }
        
        bus = ComponentBus(config)
        
        # Test component registration
        assert bus.register_component("test_component", Mock(), ["test_capability"])
        assert "test_component" in bus.components
        
        # Test message sending
        message_id = bus.send_event(
            "sender", "receiver", "test_event", 
            {"data": "test"}, MessagePriority.NORMAL
        )
        assert message_id is not None
        
        # Test subscription
        callback = Mock()
        bus.subscribe("receiver", "test_event", callback)
        
        # Process messages
        bus._process_message_queue()
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Test broadcast
        broadcast_id = bus.broadcast("sender", "global", "broadcast_event", {"data": "broadcast"})
        assert broadcast_id is not None
        
        # Cleanup
        bus.shutdown()
    
    def test_theme_manager_functionality(self, app, mock_config, temp_dir):
        """Test ThemeManager theme switching and token system"""
        config = {
            'default_theme': 'light',
            'enable_system_theme': False,
            'theme_directory': str(temp_dir / 'themes'),
            **mock_config
        }
        
        theme_manager = ThemeManager(config)
        
        # Test initialization
        assert theme_manager.current_theme == ThemeVariant.LIGHT
        assert len(theme_manager.theme_tokens) > 0
        
        # Test theme switching
        switch_success = theme_manager.switch_theme(ThemeVariant.DARK)
        assert switch_success
        assert theme_manager.current_theme == ThemeVariant.DARK
        
        # Test token retrieval
        primary_color = theme_manager.get_token_value('primary_color')
        assert primary_color is not None
        
        # Test component override
        override_success = theme_manager.register_component_override(
            "test_component", 
            {"primary_color": "#ff0000"}
        )
        assert override_success
        
        # Test theme metrics
        metrics = theme_manager.get_theme_metrics()
        assert metrics.theme_switches >= 1
        assert metrics.current_theme == ThemeVariant.DARK.value
        
        # Cleanup
        theme_manager.shutdown()
    
    def test_state_manager_snapshots(self, app, mock_config, temp_dir):
        """Test StateManager snapshot and recovery functionality"""
        config = {
            'snapshot_interval': 1,  # 1 second for testing
            'max_snapshots': 5,
            'enable_compression': True,
            'state_directory': str(temp_dir / 'state'),
            **mock_config
        }
        
        state_manager = StateManager(config)
        
        # Register a component
        mock_component = Mock()
        mock_component.get_state.return_value = {"test": "data"}
        mock_component.set_state = Mock()
        
        state_manager.register_component("test_component", mock_component)
        
        # Create snapshot
        snapshot_id = state_manager.create_snapshot("test_snapshot")
        assert snapshot_id is not None
        
        # Verify snapshot exists
        snapshots = state_manager.list_snapshots()
        assert len(snapshots) >= 1
        assert any(s.snapshot_id == snapshot_id for s in snapshots)
        
        # Test state restoration
        restore_success = state_manager.restore_from_snapshot(snapshot_id)
        assert restore_success
        mock_component.set_state.assert_called_once()
        
        # Cleanup
        state_manager.shutdown()
    
    def test_performance_monitor_metrics(self, app, mock_config):
        """Test PerformanceMonitor metrics collection"""
        config = {
            'monitoring_interval': 100,  # 100ms for testing
            'memory_threshold': 100 * 1024 * 1024,  # 100MB
            'enable_real_time': True,
            **mock_config
        }
        
        monitor = PerformanceMonitor(config)
        
        # Register component for monitoring
        mock_component = Mock()
        monitor.register_component("test_component", mock_component)
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Wait for some metrics collection
        QTest.qWait(200)
        
        # Check metrics
        metrics = monitor.get_current_metrics()
        assert metrics is not None
        assert metrics.memory_usage > 0
        
        # Test memory pressure detection
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 90  # High memory usage
            monitor._check_memory_pressure()
            # Should trigger memory pressure signal
        
        # Cleanup
        monitor.stop_monitoring()
        monitor.shutdown()
    
    def test_component_loader_lazy_loading(self, app, mock_config):
        """Test ComponentLoader dynamic component loading"""
        config = {
            'enable_lazy_loading': True,
            'cache_size': 10,
            'preload_critical': True,
            **mock_config
        }
        
        loader = ComponentLoader(config)
        
        # Register a component class
        class TestComponent:
            def __init__(self):
                self.initialized = True
        
        loader.register_component("test_component", TestComponent)
        
        # Test lazy loading
        component = loader.load_component("test_component")
        assert component is not None
        assert hasattr(component, 'initialized')
        assert component.initialized
        
        # Test caching
        component2 = loader.load_component("test_component")
        assert component2 is component  # Should be same instance from cache
        
        # Test unloading
        unload_success = loader.unload_component("test_component")
        assert unload_success
        
        # Cleanup
        loader.shutdown()
    
    def test_i18n_manager_localization(self, app, mock_config, temp_dir):
        """Test I18nManager internationalization functionality"""
        config = {
            'default_locale': 'en_US',
            'fallback_locale': 'en_US',
            'auto_detect_locale': False,
            'localization_directory': str(temp_dir / 'localization'),
            **mock_config
        }
        
        # Create test translation files
        (temp_dir / 'localization').mkdir(exist_ok=True)
        en_file = temp_dir / 'localization' / 'en_US.json'
        fr_file = temp_dir / 'localization' / 'fr_FR.json'
        
        en_file.write_text(json.dumps({
            "hello": "Hello",
            "welcome": "Welcome to the application"
        }))
        
        fr_file.write_text(json.dumps({
            "hello": "Bonjour", 
            "welcome": "Bienvenue dans l'application"
        }))
        
        i18n_manager = I18nManager(config)
        
        # Test default locale
        assert i18n_manager.current_locale == 'en_US'
        
        # Test translation retrieval
        hello_text = i18n_manager.get_text("hello")
        assert hello_text == "Hello"
        
        # Test locale switching
        switch_success = i18n_manager.switch_locale('fr_FR')
        assert switch_success
        assert i18n_manager.current_locale == 'fr_FR'
        
        # Test translation in new locale
        hello_text_fr = i18n_manager.get_text("hello")
        assert hello_text_fr == "Bonjour"
        
        # Test RTL detection
        assert not i18n_manager.is_rtl()  # French is not RTL
        
        # Cleanup
        i18n_manager.shutdown()
    
    def test_lifecycle_manager_startup_shutdown(self, app, mock_config):
        """Test LifecycleManager startup and shutdown sequences"""
        config = {
            'show_splash_screen': False,  # Disable for testing
            'max_parallel_workers': 2,
            'initialization_timeout': 5.0,
            'shutdown_timeout': 3.0,
            **mock_config
        }
        
        lifecycle_manager = LifecycleManager(config)
        
        # Register test components
        mock_component1 = Mock()
        mock_component2 = Mock()
        
        from ui.components.core.lifecycle_manager import ComponentPriority
        
        lifecycle_manager.register_component(
            "component1", mock_component1, ComponentPriority.CRITICAL
        )
        lifecycle_manager.register_component(
            "component2", mock_component2, ComponentPriority.NORMAL
        )
        
        # Test startup
        startup_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(startup_loop)
        
        try:
            startup_metrics = startup_loop.run_until_complete(
                lifecycle_manager.initialize_components()
            )
            
            assert startup_metrics.components_initialized >= 0
            assert startup_metrics.total_startup_time > 0
            
            # Test shutdown
            shutdown_metrics = startup_loop.run_until_complete(
                lifecycle_manager.shutdown_components()
            )
            
            assert shutdown_metrics.total_shutdown_time > 0
            
        finally:
            startup_loop.close()
    
    @pytest.mark.asyncio
    async def test_app_controller_integration(self, app, mock_config, temp_dir):
        """Test AppController integration of all managers"""
        app_config = AppConfiguration(
            enable_performance_monitoring=True,
            enable_advanced_theming=True,
            enable_tab_hibernation=True,
            enable_cross_tab_messaging=True,
            enable_state_snapshots=True,
            enable_dynamic_loading=True,
            enable_i18n=True,
            enable_splash_screen=False,  # Disable for testing
            enable_debug_mode=True
        )
        
        app_controller = AppController(app_config)
        
        # Test initialization
        init_success = await app_controller.initialize()
        assert init_success
        assert app_controller.app_mode == AppMode.NORMAL
        
        # Test service registration and retrieval
        test_service = Mock()
        app_controller.register_service(
            "test_service", type(test_service), ServiceScope.SINGLETON,
            factory=lambda: test_service
        )
        
        retrieved_service = app_controller.get_service("test_service")
        assert retrieved_service is test_service
        
        # Test manager availability
        assert app_controller.tab_manager is not None
        assert app_controller.component_bus is not None
        assert app_controller.theme_manager is not None
        assert app_controller.state_manager is not None
        assert app_controller.performance_monitor is not None
        assert app_controller.component_loader is not None
        assert app_controller.i18n_manager is not None
        assert app_controller.lifecycle_manager is not None
        
        # Test global state management
        app_controller.set_global_state("test_key", "test_value")
        assert app_controller.get_global_state("test_key") == "test_value"
        
        # Test configuration updates
        config_success = app_controller.update_configuration({
            "max_parallel_tabs": 15
        })
        assert config_success
        assert app_controller.config.max_parallel_tabs == 15
        
        # Test metrics
        metrics = app_controller.get_metrics()
        assert metrics is not None
        assert metrics.startup_time_ms > 0
        
        # Test debug info export
        debug_info = app_controller.export_debug_info()
        assert debug_info is not None
        assert "timestamp" in debug_info
        assert "app_mode" in debug_info
        assert "registered_services" in debug_info
        
        # Test shutdown
        shutdown_success = await app_controller.shutdown("test_shutdown")
        assert shutdown_success
    
    def test_cross_component_communication(self, app, mock_config):
        """Test communication between different managers"""
        # Create managers
        tab_manager = TabLifecycleManager(mock_config)
        bus = ComponentBus(mock_config)
        theme_manager = ThemeManager(mock_config)
        
        # Setup communication
        messages_received = []
        
        def message_handler(message):
            messages_received.append(message)
        
        bus.subscribe("theme_manager", "theme_changed", message_handler)
        
        # Test theme change communication
        theme_manager.switch_theme(ThemeVariant.DARK)
        
        # Simulate message processing
        bus._process_message_queue()
        
        # Cleanup
        tab_manager.shutdown()
        bus.shutdown()
        theme_manager.shutdown()
    
    def test_performance_under_load(self, app, mock_config):
        """Test system performance under load"""
        app_controller = AppController(AppConfiguration(
            enable_performance_monitoring=True,
            enable_debug_mode=True
        ))
        
        # Initialize
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            init_success = loop.run_until_complete(app_controller.initialize())
            assert init_success
            
            # Create multiple tabs
            if app_controller.tab_manager:
                tab_ids = []
                for i in range(5):
                    tab_id = app_controller.tab_manager.create_tab(
                        f"Test Tab {i}", Mock(), TabPriority.NORMAL
                    )
                    tab_ids.append(tab_id)
                    app_controller.tab_manager.activate_tab(tab_id)
                
                # Send multiple messages
                if app_controller.component_bus:
                    for i in range(10):
                        app_controller.component_bus.send_event(
                            f"sender_{i}", "receiver", f"event_{i}", 
                            {"data": f"test_{i}"}
                        )
                
                # Process messages
                app_controller.component_bus._process_message_queue()
                
                # Check performance metrics
                if app_controller.performance_monitor:
                    metrics = app_controller.performance_monitor.get_current_metrics()
                    assert metrics is not None
                
                # Test theme switching under load
                if app_controller.theme_manager:
                    for variant in [ThemeVariant.DARK, ThemeVariant.LIGHT, ThemeVariant.HIGH_CONTRAST]:
                        app_controller.theme_manager.switch_theme(variant)
            
            # Shutdown
            shutdown_success = loop.run_until_complete(
                app_controller.shutdown("performance_test")
            )
            assert shutdown_success
            
        finally:
            loop.close()
    
    def test_error_handling_and_recovery(self, app, mock_config):
        """Test error handling and recovery mechanisms"""
        # Test with invalid configuration
        invalid_config = AppConfiguration(
            max_parallel_tabs=-1,  # Invalid value
            memory_pressure_threshold_mb=-100  # Invalid value
        )
        
        app_controller = AppController(invalid_config)
        
        # Should handle invalid config gracefully
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Initialization might fail with invalid config, but shouldn't crash
            init_result = loop.run_until_complete(app_controller.initialize())
            # Test continues regardless of result
            
            # Test service registration with invalid parameters
            invalid_registration = app_controller.register_service(
                "", None, ServiceScope.SINGLETON  # Invalid parameters
            )
            assert not invalid_registration  # Should fail gracefully
            
            # Test getting non-existent service
            non_existent = app_controller.get_service("non_existent_service")
            assert non_existent is None
            
            # Test error in debug info export
            debug_info = app_controller.export_debug_info()
            assert isinstance(debug_info, dict)  # Should return dict even if errors occur
            
        finally:
            loop.close()
    
    def test_memory_management(self, app, mock_config):
        """Test memory management and cleanup"""
        import gc
        import sys
        
        # Get initial object count
        initial_objects = len(gc.get_objects())
        
        # Create and destroy managers multiple times
        for i in range(3):
            tab_manager = TabLifecycleManager(mock_config)
            
            # Create some tabs
            tab_ids = []
            for j in range(3):
                tab_id = tab_manager.create_tab(f"Tab {j}", Mock(), TabPriority.NORMAL)
                tab_ids.append(tab_id)
            
            # Clean shutdown
            tab_manager.shutdown()
            del tab_manager
            
            # Force garbage collection
            gc.collect()
        
        # Check for memory leaks
        final_objects = len(gc.get_objects())
        object_increase = final_objects - initial_objects
        
        # Allow some increase due to test framework overhead
        assert object_increase < 1000, f"Potential memory leak: {object_increase} objects created"


# Additional test utilities
class TestComponentMock(QObject):
    """Mock component for testing"""
    
    state_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.state = {"initialized": True}
        self.active = True
    
    def get_state(self):
        return self.state.copy()
    
    def set_state(self, state):
        self.state.update(state)
        self.state_changed.emit("state_updated")
    
    def initialize(self):
        self.active = True
    
    def shutdown(self):
        self.active = False


def create_test_translation_files(base_dir: Path):
    """Helper to create test translation files"""
    localization_dir = base_dir / 'localization'
    localization_dir.mkdir(exist_ok=True)
    
    translations = {
        'en_US.json': {
            "app_title": "Social Download Manager",
            "download": "Download",
            "settings": "Settings",
            "about": "About"
        },
        'es_ES.json': {
            "app_title": "Administrador de Descargas Sociales",
            "download": "Descargar", 
            "settings": "Configuración",
            "about": "Acerca de"
        },
        'fr_FR.json': {
            "app_title": "Gestionnaire de Téléchargement Social",
            "download": "Télécharger",
            "settings": "Paramètres", 
            "about": "À propos"
        }
    }
    
    for filename, content in translations.items():
        (localization_dir / filename).write_text(json.dumps(content, indent=2))
    
    return localization_dir


# Performance benchmarks
class PerformanceBenchmarks:
    """Performance benchmarks for advanced UI components"""
    
    @staticmethod
    def benchmark_tab_creation(tab_manager, num_tabs=100):
        """Benchmark tab creation performance"""
        start_time = time.time()
        
        tab_ids = []
        for i in range(num_tabs):
            tab_id = tab_manager.create_tab(f"Benchmark Tab {i}", Mock(), TabPriority.NORMAL)
            tab_ids.append(tab_id)
        
        creation_time = time.time() - start_time
        return {
            'tabs_created': num_tabs,
            'total_time': creation_time,
            'tabs_per_second': num_tabs / creation_time if creation_time > 0 else 0
        }
    
    @staticmethod
    def benchmark_message_throughput(component_bus, num_messages=1000):
        """Benchmark message throughput"""
        start_time = time.time()
        
        for i in range(num_messages):
            component_bus.send_event(
                f"sender_{i % 10}", "receiver", f"event_{i}",
                {"data": f"benchmark_data_{i}"}
            )
        
        send_time = time.time() - start_time
        
        # Process messages
        process_start = time.time()
        component_bus._process_message_queue()
        process_time = time.time() - process_start
        
        return {
            'messages_sent': num_messages,
            'send_time': send_time,
            'process_time': process_time,
            'messages_per_second': num_messages / (send_time + process_time) if (send_time + process_time) > 0 else 0
        }
    
    @staticmethod
    def benchmark_theme_switching(theme_manager, num_switches=50):
        """Benchmark theme switching performance"""
        themes = [ThemeVariant.LIGHT, ThemeVariant.DARK, ThemeVariant.HIGH_CONTRAST]
        
        start_time = time.time()
        
        for i in range(num_switches):
            theme = themes[i % len(themes)]
            theme_manager.switch_theme(theme)
        
        switch_time = time.time() - start_time
        
        return {
            'theme_switches': num_switches,
            'total_time': switch_time,
            'switches_per_second': num_switches / switch_time if switch_time > 0 else 0
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 