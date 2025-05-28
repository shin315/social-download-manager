"""
Configuration Manager for Social Download Manager v2.0

Handles application configuration, settings, and environment variables.
Provides centralized configuration management for all modules.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class PlatformConfig:
    """Configuration for a specific platform"""
    enabled: bool = True
    max_concurrent_downloads: int = 3
    default_quality: str = "best"
    custom_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_settings is None:
            self.custom_settings = {}


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    path: str = "data/downloads.db"
    backup_enabled: bool = True
    backup_interval_days: int = 7
    max_backups: int = 5


@dataclass
class UIConfig:
    """User interface configuration"""
    theme: str = "light"
    language: str = "en"
    window_width: int = 1200
    window_height: int = 800
    auto_save_settings: bool = True


@dataclass
class DownloadConfig:
    """Download-related configuration"""
    default_directory: str = "downloads"
    create_subdirectories: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    parallel_downloads: int = 3


@dataclass
class AppConfig:
    """Main application configuration"""
    version: str = "2.0.0-dev"
    app_name: str = "Social Download Manager"
    platforms: Dict[str, PlatformConfig] = None
    database: DatabaseConfig = None
    ui: UIConfig = None
    downloads: DownloadConfig = None
    
    def __post_init__(self):
        if self.platforms is None:
            self.platforms = {
                "tiktok": PlatformConfig(),
                "youtube": PlatformConfig(enabled=False),  # Future platform
                "instagram": PlatformConfig(enabled=False),  # Future platform
                "facebook": PlatformConfig(enabled=False),  # Future platform
            }
        if self.database is None:
            self.database = DatabaseConfig()
        if self.ui is None:
            self.ui = UIConfig()
        if self.downloads is None:
            self.downloads = DownloadConfig()


class ConfigManager:
    """Manages application configuration and settings"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager
        
        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        self.config_path = Path(config_path) if config_path else Path("config.json")
        self._config: Optional[AppConfig] = None
        self._load_config()
    
    def _get_default_config(self) -> AppConfig:
        """Get default configuration"""
        return AppConfig()
    
    def _load_config(self) -> None:
        """Load configuration from file or create default"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._config = self._dict_to_config(config_data)
            else:
                self._config = self._get_default_config()
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = self._get_default_config()
    
    def _dict_to_config(self, data: Dict[str, Any]) -> AppConfig:
        """Convert dictionary to AppConfig object"""
        # Convert platform configs
        platforms = {}
        if "platforms" in data:
            for name, platform_data in data["platforms"].items():
                platforms[name] = PlatformConfig(**platform_data)
        
        # Convert other configs
        database = DatabaseConfig(**data.get("database", {}))
        ui = UIConfig(**data.get("ui", {}))
        downloads = DownloadConfig(**data.get("downloads", {}))
        
        return AppConfig(
            version=data.get("version", "2.0.0-dev"),
            app_name=data.get("app_name", "Social Download Manager"),
            platforms=platforms,
            database=database,
            ui=ui,
            downloads=downloads
        )
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert AppConfig to dictionary"""
        if not self._config:
            return {}
        
        config_dict = asdict(self._config)
        return config_dict
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            config_dict = self._config_to_dict()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @property
    def config(self) -> AppConfig:
        """Get current configuration"""
        if self._config is None:
            self._load_config()
        return self._config
    
    def get_platform_config(self, platform: str) -> Optional[PlatformConfig]:
        """Get configuration for specific platform"""
        return self.config.platforms.get(platform)
    
    def update_platform_config(self, platform: str, config: PlatformConfig) -> bool:
        """Update configuration for specific platform"""
        self.config.platforms[platform] = config
        return self.save_config()
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return self.config.database
    
    def get_ui_config(self) -> UIConfig:
        """Get UI configuration"""
        return self.config.ui
    
    def get_download_config(self) -> DownloadConfig:
        """Get download configuration"""
        return self.config.downloads
    
    def set_setting(self, section: str, key: str, value: Any) -> bool:
        """Set a specific setting value"""
        try:
            section_obj = getattr(self.config, section)
            setattr(section_obj, key, value)
            return self.save_config()
        except AttributeError:
            return False
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific setting value"""
        try:
            section_obj = getattr(self.config, section)
            return getattr(section_obj, key, default)
        except AttributeError:
            return default


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get the current application configuration"""
    return get_config_manager().config 