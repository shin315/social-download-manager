#!/usr/bin/env python3
"""
Social Download Manager v2.0 - Main Entry Point

Multi-platform social media content downloader with modular architecture.
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Core imports
from core.config_manager import get_config_manager, get_config
from core.event_system import get_event_bus, publish_event, EventType
from core.app_controller import get_app_controller, initialize_app_controller, shutdown_app_controller
from core.constants import (
    AppConstants, PlatformConstants, UIConstants, DatabaseConstants, ErrorConstants,
    validate_constants, get_platform_name, is_supported_platform
)
from version import get_version_info, get_full_version, is_development_version

# Platform imports (will be implemented in later tasks)
# from platforms.platform_factory import PlatformFactory
# from platforms.tiktok.tiktok_handler import TikTokHandler

# UI imports (will be refactored in later tasks)
# from ui.main_window import MainWindow

# Data imports (will be implemented in later tasks)
# from data.database.connection import DatabaseManager

def setup_application() -> bool:
    """
    Setup the application environment and configuration using App Controller
    
    Returns:
        True if setup successful, False otherwise
    """
    try:
        # Validate constants first
        print("Validating application constants...")
        if not validate_constants():
            print("❌ Constants validation failed!")
            return False
        print("✅ Constants validation passed")
        
        # Initialize App Controller (this will initialize all core systems)
        print(f"Initializing {AppConstants.APP_NAME} v{AppConstants.APP_VERSION} with App Controller...")
        if not initialize_app_controller():
            print("❌ App Controller initialization failed!")
            return False
        print("✅ App Controller initialized successfully")
        
        # Get controller instance for further operations
        controller = get_app_controller()
        
        # Get components from controller
        config_manager = controller.get_component("config_manager")
        event_bus = controller.get_component("event_bus")
        config = controller.get_config()
        
        if not config_manager or not event_bus or not config:
            print("❌ Failed to get core components from controller!")
            return False
        
        # Validate configuration
        if not config_manager.config_path.exists():
            print("Creating default configuration...")
            config_manager.save_config()
        
        print(f"Configuration loaded from: {config_manager.config_path}")
        print(f"Development mode: {is_development_version()}")
        print(f"App Controller status: {controller.get_status().state.name}")
        
        # Print platform status using constants
        print("\nPlatform Status:")
        for platform_id in PlatformConstants.PLATFORM_NAMES.keys():
            platform_name = get_platform_name(platform_id)
            is_supported = is_supported_platform(platform_id)
            status = PlatformConstants.PLATFORM_STATUS.get(platform_id, "unknown")
            status_emoji = "✅" if status == PlatformConstants.STATUS_STABLE else "⏳" if status == PlatformConstants.STATUS_PLANNED else "❌"
            print(f"  {status_emoji} {platform_name}: {status.upper()}")
        
        # Test constants access
        print(f"\nConstants Test:")
        print(f"  App Short Name: {AppConstants.APP_SHORT_NAME}")
        print(f"  Default Timeout: {AppConstants.DEFAULT_TIMEOUT}s")
        print(f"  Max Concurrent Downloads: {AppConstants.MAX_CONCURRENT_DOWNLOADS}")
        print(f"  Supported Languages: {len(UIConstants.AVAILABLE_LANGUAGES)}")
        print(f"  Download Statuses: {len(DatabaseConstants.DOWNLOAD_STATUSES)}")
        
        # Test controller status
        status = controller.get_status()
        print(f"\nApp Controller Status:")
        print(f"  State: {status.state.name}")
        print(f"  Components: {', '.join(status.components_initialized)}")
        print(f"  Ready: {controller.is_ready()}")
        
        return True
        
    except Exception as e:
        print(f"Error during application setup: {e}")
        return False


def main() -> int:
    """
    Main application entry point
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Print version information
    version_info = get_version_info()
    print(f"{get_full_version()}")
    print(f"Python {sys.version}")
    print("-" * 50)
    
    # Setup application
    if not setup_application():
        print("Failed to setup application")
        return 1
    
    try:
        # For v2.0 development, check if we're in compatibility mode
        config = get_config()
        
        if is_development_version():
            print("\n🚧 DEVELOPMENT VERSION 🚧")
            print("This is a development version of Social Download Manager v2.0")
            print("New architecture components are being built incrementally.")
            print("\nFor stable TikTok downloads, use the v1.2.1 version:")
            print("  python main.py")
            print("\nv2.0 Status:")
            print("  ✅ Configuration system")
            print("  ✅ Event system")
            print("  ✅ Constants management")
            print("  ✅ Project structure")
            print("  ⏳ Platform abstraction (Task 4)")
            print("  ⏳ Database layer (Task 5)")
            print("  ⏳ UI refactoring (Task 6+)")
            
            # For now, offer to run v1.2.1 or continue with v2.0 development
            print("\nOptions:")
            print("  1. Run stable v1.2.1 version")
            print("  2. Continue with v2.0 development")
            print("  3. Exit")
            
            try:
                choice = input("\nEnter choice (1-3): ").strip()
                
                if choice == "1":
                    print("\nLaunching v1.2.1...")
                    import subprocess
                    return subprocess.call([sys.executable, "main.py"])
                    
                elif choice == "2":
                    print("\n🔧 v2.0 Development Mode")
                    print("Core systems initialized successfully!")
                    print("Ready for incremental development...")
                    
                    # Test configuration system
                    print(f"\nConfiguration test:")
                    print(f"  App name: {config.app_name}")
                    print(f"  Version: {config.version}")
                    print(f"  Platforms configured: {len(config.platforms)}")
                    
                    # Test event system
                    event_bus = get_event_bus()
                    print(f"  Event system: {event_bus.get_total_subscribers()} subscribers")
                    
                    # Test constants system
                    print(f"\nConstants system test:")
                    print(f"  Platform constants: {len(PlatformConstants.PLATFORM_NAMES)} platforms")
                    print(f"  Error codes: {len(ErrorConstants.ERROR_CODES)} defined")
                    print(f"  UI themes: {UIConstants.AVAILABLE_THEMES}")
                    print(f"  Quality options: {PlatformConstants.QUALITY_OPTIONS}")
                    
                    print("\n✅ v2.0 foundation ready for Task 4!")
                    return 0
                    
                elif choice == "3":
                    print("Goodbye!")
                    return 0
                    
                else:
                    print("Invalid choice")
                    return 1
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                return 0
                
        else:
            # Production mode - launch full application
            print("Launching Social Download Manager v2.0...")
            
            # Import and launch main UI (will be implemented in later tasks)
            # app = QApplication(sys.argv)
            # main_window = MainWindow()
            # main_window.show()
            # return app.exec()
            
            print("Production mode not yet implemented")
            return 1
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        controller = get_app_controller()
        if controller:
            controller.handle_error(e, "main_application")
        return 1
    
    finally:
        # Always cleanup App Controller on exit
        print("\nShutting down App Controller...")
        if shutdown_app_controller():
            print("✅ App Controller shutdown complete")
        else:
            print("⚠️ App Controller shutdown had issues")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 