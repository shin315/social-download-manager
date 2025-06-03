#!/usr/bin/env python3
"""
v2.0 Architecture Component Fixtures for Integration Testing

This module provides pytest fixtures for setting up v2.0 architecture components
in isolated test environments for integration testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.main_entry_orchestrator import (
        MainEntryOrchestrator, StartupConfig, StartupMode, create_default_startup_config
    )
    from core.adapter_integration import (
        AdapterIntegrationFramework, IntegrationConfig, IntegrationState, 
        create_default_integration_config
    )
    from core.error_management import ErrorManager, ErrorCode, ErrorSeverity
    from core.logging_system import LoggingSystem, get_logger
    from core.shutdown_manager import ShutdownManager, ShutdownReason
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False


@pytest.fixture
def temp_test_dir():
    """Create temporary directory for test files"""
    temp_dir = Path(tempfile.mkdtemp(prefix="v2_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture  
def mock_startup_config():
    """Create mock startup configuration for testing"""
    if not CORE_AVAILABLE:
        pytest.skip("Core components not available")
    
    config = create_default_startup_config()
    config.feature_flags.update({
        "enable_debug_logging": True,
        "enable_performance_monitoring": True,
        "skip_non_critical_components": True,
        "allow_partial_initialization": True
    })
    config.phase_timeout = 5.0  # Shorter timeout for tests
    config.component_timeout = 2.0
    return config


@pytest.fixture
def mock_integration_config():
    """Create mock integration configuration for testing"""
    if not CORE_AVAILABLE:
        pytest.skip("Core components not available")
    
    config = create_default_integration_config()
    config.health_check_interval_ms = 1000  # Faster health checks for tests
    config.performance_thresholds.response_time_ms = 200  # More lenient for tests
    return config


@pytest.fixture
def main_entry_orchestrator(mock_startup_config):
    """Create MainEntryOrchestrator for testing"""
    if not CORE_AVAILABLE:
        pytest.skip("Core components not available")
    
    orchestrator = MainEntryOrchestrator(mock_startup_config)
    yield orchestrator
    
    # Cleanup
    try:
        if hasattr(orchestrator, '_qt_application') and orchestrator._qt_application:
            orchestrator._qt_application.quit()
    except:
        pass


@pytest.fixture
def adapter_integration_framework(mock_integration_config):
    """Create AdapterIntegrationFramework for testing"""
    if not CORE_AVAILABLE:
        pytest.skip("Core components not available")
    
    framework = AdapterIntegrationFramework(mock_integration_config)
    yield framework
    
    # Cleanup
    try:
        framework.shutdown()
    except:
        pass


@pytest.fixture
def error_manager():
    """Create ErrorManager for testing"""
    if not CORE_AVAILABLE:
        pytest.skip("Core components not available")
    
    manager = ErrorManager()
    yield manager
    
    # Cleanup
    try:
        manager.clear_errors()
    except:
        pass


@pytest.fixture
def logging_system():
    """Create LoggingSystem for testing"""
    if not CORE_AVAILABLE:
        pytest.skip("Core components not available")
    
    system = LoggingSystem()
    yield system
    
    # Cleanup
    try:
        system.shutdown()
    except:
        pass


@pytest.fixture
def shutdown_manager():
    """Create ShutdownManager for testing"""
    if not CORE_AVAILABLE:
        pytest.skip("Core components not available")
    
    manager = ShutdownManager()
    yield manager
    
    # Cleanup
    try:
        manager.force_shutdown()
    except:
        pass


@pytest.fixture
def mock_v2_components():
    """Create mock v2.0 components for testing"""
    components = {
        'config_manager': Mock(),
        'event_bus': Mock(),
        'app_controller': Mock(),
        'database_manager': Mock(),
        'service_registry': Mock(),
        'platform_factory': Mock()
    }
    
    # Setup mock behaviors
    components['config_manager'].get_config.return_value = {'test': True}
    components['event_bus'].publish.return_value = True
    components['app_controller'].initialize.return_value = True
    components['database_manager'].connect.return_value = True
    components['service_registry'].register.return_value = True
    components['platform_factory'].create.return_value = Mock()
    
    return components 