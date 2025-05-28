"""
Core module for Social Download Manager v2.0

This module contains the core business logic and orchestration components
that are independent of specific platforms or UI implementations.
"""

__version__ = "2.0.0-dev"
__author__ = "Social Download Manager Team"

# Export core components
from .app_controller import (
    AppController, IAppController, ControllerState, ControllerStatus, ControllerError,
    get_app_controller, initialize_app_controller, shutdown_app_controller
)

from .config_manager import (
    ConfigManager, AppConfig, PlatformConfig, DatabaseConfig, UIConfig, DownloadConfig,
    get_config_manager, get_config
)

from .event_system import (
    EventBus, Event, EventType, EventHandler,
    get_event_bus, publish_event, subscribe_to_event
)

from .constants import (
    AppConstants, PlatformConstants, UIConstants, DatabaseConstants, ErrorConstants,
    validate_constants, get_platform_name, is_supported_platform
) 