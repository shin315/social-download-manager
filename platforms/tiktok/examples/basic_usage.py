#!/usr/bin/env python3
"""
Basic TikTok Handler Usage Examples

This example demonstrates the fundamental operations of the TikTok handler:
- Initializing the handler
- Checking URL validity
- Retrieving video information
- Downloading videos

Requirements:
- pip install yt-dlp
- Proper project structure with platforms.tiktok module
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from platforms.tiktok import TikTokHandler
from core.services.platform_factory import PlatformFactory


async def basic_video_info_example():
    """Example: Get basic video information"""
    print("=" * 60)
    print("BASIC VIDEO INFO EXAMPLE")
    print("=" * 60)
    
    # Initialize handler with basic config
    config = {
        'enable_caching': True,
        'enable_concurrent_processing': False,  # Disable for simplicity
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 30,
            'min_request_interval': 2.0
        }
    }
    
    handler = TikTokHandler(config=config)
    
    # Test URLs (replace with actual TikTok URLs)
    test_urls = [
        "https://www.tiktok.com/@username/video/1234567890123456789",
        "https://vm.tiktok.com/shortcode",
        "https://m.tiktok.com/v/1234567890123456789.html"
    ]
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        
        # Check if URL is valid
        if handler.is_valid_url(url):
            print("✅ URL is valid for TikTok handler")
            
            try:
                # Get video information
                print("🔍 Retrieving video information...")
                video_info = await handler.get_video_info(url)
                
                # Display basic information
                print(f"📹 Title: {video_info.title}")
                print(f"👤 Creator: {video_info.creator}")
                print(f"⏱️  Duration: {video_info.duration}s")
                print(f"📊 Views: {video_info.view_count:,}")
                print(f"❤️  Likes: {video_info.like_count:,}")
                print(f"💬 Comments: {video_info.comment_count:,}")
                print(f"🔗 Platform URL: {video_info.platform_url}")
                
                # Show available qualities
                if video_info.available_qualities:
                    print(f"📺 Available qualities: {', '.join(video_info.available_qualities)}")
                
                # Show hashtags
                if hasattr(video_info, 'hashtags') and video_info.hashtags:
                    hashtags = video_info.hashtags[:5]  # Show first 5
                    print(f"🏷️  Hashtags: {', '.join(hashtags)}")
                
                print("✅ Video information retrieved successfully!")
                
            except Exception as e:
                print(f"❌ Failed to get video info: {e}")
        else:
            print("❌ URL is not valid for TikTok handler")


async def basic_download_example():
    """Example: Download a TikTok video"""
    print("\n" + "=" * 60)
    print("BASIC DOWNLOAD EXAMPLE")
    print("=" * 60)
    
    # Initialize handler with download-optimized config
    config = {
        'enable_caching': True,
        'enable_concurrent_processing': True,
        'max_concurrent_operations': 3,
        'rate_limit': {
            'enabled': True,
            'requests_per_minute': 30
        }
    }
    
    handler = TikTokHandler(config=config)
    
    # Test URL (replace with actual TikTok URL)
    test_url = "https://www.tiktok.com/@username/video/1234567890123456789"
    
    if not handler.is_valid_url(test_url):
        print("❌ Invalid URL provided")
        return
    
    # Create downloads directory
    download_dir = Path("downloads/tiktok_examples")
    download_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 Download directory: {download_dir.absolute()}")
    print(f"🔗 Downloading from: {test_url}")
    
    try:
        # Simple progress callback
        def progress_callback(info):
            if info.get('status') == 'downloading':
                percent = info.get('_percent_str', 'N/A')
                speed = info.get('_speed_str', 'N/A')
                print(f"⬇️  Progress: {percent} | Speed: {speed}", end='\r')
            elif info.get('status') == 'finished':
                print(f"\n✅ Download completed: {info.get('filename', 'Unknown')}")
        
        # Download with basic quality preference
        download_options = {
            'output_path': str(download_dir),
            'quality_preference': 'HD',  # HD, SD, or LD
            'include_audio': True,
            'progress_callback': progress_callback
        }
        
        print("🚀 Starting download...")
        result = await handler.download_video(test_url, download_options)
        
        if result.success:
            print(f"🎉 Download successful!")
            print(f"📁 File path: {result.file_path}")
            print(f"📏 File size: {result.file_size / (1024*1024):.2f} MB")
            print(f"🎬 Format: {result.format}")
            print(f"📊 Quality: {result.quality}")
        else:
            print(f"❌ Download failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Download error: {e}")


async def handler_capabilities_example():
    """Example: Check handler capabilities"""
    print("\n" + "=" * 60)
    print("HANDLER CAPABILITIES EXAMPLE")
    print("=" * 60)
    
    handler = TikTokHandler()
    capabilities = handler.get_capabilities()
    
    print(f"🏷️  Platform Name: {capabilities.platform_name}")
    print(f"📝 Supports Info: {capabilities.supports_video_info}")
    print(f"⬇️  Supports Download: {capabilities.supports_download}")
    print(f"🔐 Requires Auth: {capabilities.requires_authentication}")
    print(f"📊 Max Quality: {capabilities.max_quality.name}")
    print(f"🎵 Supports Audio: {capabilities.supports_audio_only}")
    print(f"📹 Supports Video: {capabilities.supports_video_only}")
    print(f"📱 Supports Playlists: {capabilities.supports_playlists}")
    print(f"🔴 Supports Live: {capabilities.supports_live_streams}")
    
    # Supported formats
    print(f"🎬 Supported Formats: {', '.join(capabilities.supported_formats)}")
    
    # Quality levels
    quality_levels = [q.name for q in capabilities.quality_levels]
    print(f"📺 Quality Levels: {', '.join(quality_levels)}")


async def error_handling_example():
    """Example: Proper error handling"""
    print("\n" + "=" * 60)
    print("ERROR HANDLING EXAMPLE")
    print("=" * 60)
    
    handler = TikTokHandler()
    
    # Test various error scenarios
    error_cases = [
        ("Invalid URL", "https://not-a-tiktok-url.com"),
        ("Malformed URL", "invalid-url"),
        ("Non-existent video", "https://www.tiktok.com/@user/video/0000000000000000000"),
    ]
    
    for case_name, test_url in error_cases:
        print(f"\n🧪 Testing: {case_name}")
        print(f"🔗 URL: {test_url}")
        
        try:
            if handler.is_valid_url(test_url):
                video_info = await handler.get_video_info(test_url)
                print(f"✅ Unexpected success: {video_info.title}")
            else:
                print("❌ URL validation failed (expected)")
                
        except Exception as e:
            error_type = type(e).__name__
            print(f"⚠️  Caught {error_type}: {e}")
            
            # Check if it's a platform-specific error with context
            if hasattr(e, 'context') and e.context:
                context = e.context
                print(f"📋 Error Context:")
                print(f"   Operation: {getattr(context, 'operation', 'Unknown')}")
                print(f"   User Message: {getattr(context, 'user_message', 'N/A')}")
                if hasattr(context, 'recovery_options') and context.recovery_options:
                    print(f"   Recovery Options: {', '.join(context.recovery_options)}")


async def session_management_example():
    """Example: Session management and authentication"""
    print("\n" + "=" * 60)
    print("SESSION MANAGEMENT EXAMPLE")
    print("=" * 60)
    
    # Initialize with session management
    config = {
        'enable_authentication': True,  # Enable auth features
        'session_config': {
            'track_requests': True,
            'session_timeout': 3600,
            'auto_refresh': True
        }
    }
    
    handler = TikTokHandler(config=config)
    
    # Check initial session info
    session_info = handler.get_session_info()
    print(f"📊 Initial Session Info:")
    print(f"   Request Count: {session_info.get('request_count', 0)}")
    print(f"   Active Since: {session_info.get('created_at', 'Unknown')}")
    print(f"   Last Request: {session_info.get('last_request_time', 'None')}")
    
    # Test URL for session tracking
    test_url = "https://www.tiktok.com/@username/video/1234567890123456789"
    
    if handler.is_valid_url(test_url):
        try:
            print(f"\n🔍 Making test request to track session...")
            video_info = await handler.get_video_info(test_url)
            
            # Check updated session info
            updated_session = handler.get_session_info()
            print(f"📊 Updated Session Info:")
            print(f"   Request Count: {updated_session.get('request_count', 0)}")
            print(f"   Last Request: {updated_session.get('last_request_time', 'None')}")
            
        except Exception as e:
            print(f"⚠️  Request failed: {e}")
    
    # Demonstrate session clearing
    print(f"\n🧹 Clearing session...")
    handler.clear_session()
    
    cleared_session = handler.get_session_info()
    print(f"📊 Cleared Session Info:")
    print(f"   Request Count: {cleared_session.get('request_count', 0)}")


async def main():
    """Run all examples"""
    print("🎬 TikTok Handler Basic Usage Examples")
    print("=====================================")
    
    try:
        # Run examples
        await handler_capabilities_example()
        await basic_video_info_example()
        await basic_download_example()
        await error_handling_example()
        await session_management_example()
        
        print("\n" + "=" * 60)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n🛑 Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Examples failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Note: Replace test URLs with actual TikTok URLs for real testing
    print("⚠️  Note: Replace test URLs with actual TikTok URLs for real testing")
    print("🔗 Test URLs in this example are placeholders")
    
    # Run the examples
    asyncio.run(main()) 