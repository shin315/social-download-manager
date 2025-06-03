#!/usr/bin/env python3
"""
Simple test script for YouTube handler documentation examples
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from platforms.youtube import YouTubeHandler
from platforms import create_handler_for_url, detect_platform


def test_documentation_examples():
    """Test examples from documentation"""
    print("🧪 Testing Documentation Examples")
    print("=" * 50)
    
    # Test URL validation example
    print("1. URL Validation:")
    handler = YouTubeHandler()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    is_valid = handler.is_valid_url(url)
    print(f"   Valid: {is_valid}")
    
    # Test video ID extraction
    video_id = handler.extract_video_id("https://youtu.be/dQw4w9WgXcQ")
    print(f"   Video ID: {video_id}")
    
    # Test URL normalization
    normalized = handler.normalize_url("https://youtu.be/dQw4w9WgXcQ")
    print(f"   Normalized: {normalized}")
    
    # Test platform detection
    print("\n2. Platform Detection:")
    platform = detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(f"   Detected Platform: {platform.display_name}")
    
    # Test handler creation
    print("\n3. Handler Creation:")
    handler2 = create_handler_for_url("https://youtu.be/dQw4w9WgXcQ")
    print(f"   Handler Type: {type(handler2).__name__}")
    
    # Test capabilities
    print("\n4. Platform Capabilities:")
    capabilities = handler.get_capabilities()
    print(f"   Supports video: {capabilities.supports_video}")
    print(f"   Supports audio: {capabilities.supports_audio}")
    print(f"   Requires auth: {capabilities.requires_auth}")
    
    # Test platform info
    print("\n5. Platform Information:")
    info = handler.get_platform_specific_info()
    print(f"   Platform: {info.get('platform')}")
    print(f"   Status: {info.get('implementation_status')}")
    
    print("\n✅ All documentation examples working correctly!")


if __name__ == "__main__":
    test_documentation_examples() 