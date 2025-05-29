#!/usr/bin/env python3
"""
YouTube Handler Basic Usage Examples

This file demonstrates how to use the YouTube handler stub implementation
with various URLs and operations.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from platforms import create_handler_for_url, detect_platform, is_url_supported
from platforms.youtube import YouTubeHandler
from platforms.base import PlatformContentError


def example_url_validation():
    """Demonstrate URL validation capabilities"""
    print("🔍 YouTube URL Validation Examples")
    print("=" * 50)
    
    handler = YouTubeHandler()
    
    # Test various YouTube URL formats
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/embed/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.google.com",  # Invalid
        "not-a-url",  # Invalid
    ]
    
    for url in test_urls:
        is_valid = handler.is_valid_url(url)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"  {status}: {url}")
        
        if is_valid:
            # Extract video ID
            video_id = handler.extract_video_id(url)
            print(f"    Video ID: {video_id}")
            
            # Normalize URL
            normalized = handler.normalize_url(url)
            print(f"    Normalized: {normalized}")
        print()


def example_platform_detection():
    """Demonstrate platform detection via factory"""
    print("🏭 Platform Factory Detection Examples")
    print("=" * 50)
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.tiktok.com/@user/video/123",  # Different platform
    ]
    
    for url in test_urls:
        # Detect platform
        platform = detect_platform(url)
        print(f"URL: {url}")
        print(f"  Detected Platform: {platform.display_name}")
        
        # Check URL support
        supported = is_url_supported(url)
        print(f"  Supported: {supported}")
        
        # Create handler if supported
        if supported and platform.value == "youtube":
            handler = create_handler_for_url(url)
            print(f"  Handler Created: {type(handler).__name__}")
        print()


async def example_video_info():
    """Demonstrate getting video information (stub)"""
    print("📺 Video Information Examples (Stub)")
    print("=" * 50)
    
    handler = YouTubeHandler()
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/abcdefghijk",
    ]
    
    for url in test_urls:
        print(f"Getting info for: {url}")
        
        try:
            # Get video information
            video_info = await handler.get_video_info(url)
            
            print(f"  ✅ Success!")
            print(f"    Title: {video_info.title}")
            print(f"    Platform: {video_info.platform.display_name}")
            print(f"    Video ID: {video_info.platform_id}")
            print(f"    Duration: {video_info.duration}s")
            print(f"    Content Type: {video_info.content_type.value}")
            print(f"    Available Formats: {len(video_info.formats)}")
            
            # Show format details
            for fmt in video_info.formats:
                print(f"      - {fmt.quality.value} ({fmt.width}x{fmt.height}) .{fmt.ext}")
            
            print(f"    Stub Implementation: {video_info.extra_data.get('stub_implementation')}")
            
        except PlatformContentError as e:
            print(f"  ❌ Error: {e}")
        
        print()


async def example_download_attempt():
    """Demonstrate download attempt (stub behavior)"""
    print("⬇️ Download Attempt Examples (Stub)")
    print("=" * 50)
    
    handler = YouTubeHandler()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    output_path = Path("./downloads")
    
    print(f"Attempting download: {url}")
    print(f"Output directory: {output_path}")
    
    try:
        # Attempt download (will return stub failure)
        result = await handler.download_video(
            url=url,
            output_path=output_path,
            quality=None,  # Let handler choose
            audio_only=False
        )
        
        print(f"  Download Success: {result.success}")
        print(f"  File Path: {result.file_path}")
        print(f"  Error Message: {result.error_message}")
        print(f"  Video Info Available: {result.video_info is not None}")
        
        if result.video_info:
            print(f"    Video Title: {result.video_info.title}")
        
    except Exception as e:
        print(f"  ❌ Unexpected Error: {e}")


def example_capabilities():
    """Demonstrate platform capabilities"""
    print("⚙️ Platform Capabilities Examples")
    print("=" * 50)
    
    handler = YouTubeHandler()
    capabilities = handler.get_capabilities()
    
    print("YouTube Handler Capabilities:")
    print(f"  Supports Video: {capabilities.supports_video}")
    print(f"  Supports Audio: {capabilities.supports_audio}")
    print(f"  Supports Playlists: {capabilities.supports_playlists}")
    print(f"  Supports Live: {capabilities.supports_live}")
    print(f"  Supports Stories: {capabilities.supports_stories}")
    print(f"  Requires Authentication: {capabilities.requires_auth}")
    print(f"  Supports Quality Selection: {capabilities.supports_quality_selection}")
    print(f"  Supports Thumbnails: {capabilities.supports_thumbnails}")
    print(f"  Supports Metadata: {capabilities.supports_metadata}")
    print(f"  Max Concurrent Downloads: {capabilities.max_concurrent_downloads}")
    print()


def example_platform_info():
    """Demonstrate platform-specific information"""
    print("ℹ️ Platform-Specific Information")
    print("=" * 50)
    
    handler = YouTubeHandler()
    info = handler.get_platform_specific_info()
    
    print("YouTube Platform Information:")
    for key, value in info.items():
        if isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    - {item}")
        else:
            print(f"  {key}: {value}")
    print()


async def main():
    """Run all examples"""
    print("🎬 YouTube Handler Examples")
    print("=" * 60)
    print()
    
    # Synchronous examples
    example_url_validation()
    example_platform_detection()
    example_capabilities()
    example_platform_info()
    
    # Asynchronous examples
    await example_video_info()
    await example_download_attempt()
    
    print("=" * 60)
    print("✅ All examples completed!")
    print("Note: This is a stub implementation. Actual download functionality")
    print("will be implemented in future versions.")


if __name__ == "__main__":
    asyncio.run(main()) 