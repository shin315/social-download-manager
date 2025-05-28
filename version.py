"""
Version information for Social Download Manager v2.0

Centralized version management and build information.
"""

import datetime
from typing import NamedTuple


class VersionInfo(NamedTuple):
    """Version information structure"""
    major: int
    minor: int
    patch: int
    stage: str = "stable"  # dev, alpha, beta, rc, stable
    build: int = 0


# Current version information
VERSION_INFO = VersionInfo(2, 0, 0, "dev", 1)

# Version string
__version__ = f"{VERSION_INFO.major}.{VERSION_INFO.minor}.{VERSION_INFO.patch}"
if VERSION_INFO.stage != "stable":
    __version__ += f"-{VERSION_INFO.stage}"
    if VERSION_INFO.build > 0:
        __version__ += f".{VERSION_INFO.build}"

# Application metadata
APP_NAME = "Social Download Manager"
APP_DESCRIPTION = "Multi-platform social media content downloader"
APP_AUTHOR = "Social Download Manager Team"
APP_COPYRIGHT = f"© {datetime.datetime.now().year} {APP_AUTHOR}"
APP_LICENSE = "MIT"

# Build information
BUILD_DATE = datetime.datetime.now().isoformat()
PYTHON_REQUIRES = ">=3.8"

# Platform support
SUPPORTED_PLATFORMS = {
    "tiktok": {
        "name": "TikTok",
        "status": "stable",
        "version": "1.2.1",
        "icon": "tiktok.png"
    },
    "youtube": {
        "name": "YouTube", 
        "status": "planned",
        "version": "0.0.0",
        "icon": "youtube.png"
    },
    "instagram": {
        "name": "Instagram",
        "status": "planned", 
        "version": "0.0.0",
        "icon": "instagram.png"
    },
    "facebook": {
        "name": "Facebook",
        "status": "planned",
        "version": "0.0.0", 
        "icon": "facebook.png"
    },
    "twitter": {
        "name": "Twitter/X",
        "status": "planned",
        "version": "0.0.0",
        "icon": "twitter.png"
    }
}

# Feature flags for v2.0 development
FEATURE_FLAGS = {
    "multi_platform": True,
    "new_ui_components": True,
    "database_migration": True,
    "async_downloads": True,
    "plugin_system": False,  # Future feature
    "cloud_sync": False,     # Future feature
}

def get_version_info() -> dict:
    """Get comprehensive version information"""
    return {
        "version": __version__,
        "version_info": VERSION_INFO._asdict(),
        "app_name": APP_NAME,
        "description": APP_DESCRIPTION,
        "author": APP_AUTHOR,
        "copyright": APP_COPYRIGHT,
        "license": APP_LICENSE,
        "build_date": BUILD_DATE,
        "python_requires": PYTHON_REQUIRES,
        "supported_platforms": SUPPORTED_PLATFORMS,
        "feature_flags": FEATURE_FLAGS
    }

def get_short_version() -> str:
    """Get short version string"""
    return f"{VERSION_INFO.major}.{VERSION_INFO.minor}.{VERSION_INFO.patch}"

def get_full_version() -> str:
    """Get full version string with metadata"""
    return f"{APP_NAME} v{__version__} ({BUILD_DATE})"

def is_development_version() -> bool:
    """Check if this is a development version"""
    return VERSION_INFO.stage in ("dev", "alpha", "beta", "rc")

def get_platform_status(platform: str) -> str:
    """Get the status of a specific platform"""
    return SUPPORTED_PLATFORMS.get(platform, {}).get("status", "unknown")

def is_feature_enabled(feature: str) -> bool:
    """Check if a feature flag is enabled"""
    return FEATURE_FLAGS.get(feature, False) 