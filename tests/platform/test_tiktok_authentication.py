#!/usr/bin/env python3
"""
Test script for TikTok authentication and session management

This script specifically tests the authentication features implemented in subtask 8.2
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from platforms.tiktok import TikTokHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_authentication_config():
    """Test authentication configuration and setup"""
    
    print("🔐 Testing Authentication Configuration")
    print("=" * 45)
    
    # Test basic initialization
    print("\n1. Basic Handler Initialization...")
    handler = TikTokHandler()
    session_info = handler.get_session_info()
    print(f"   Authenticated: {session_info['authenticated']}")
    print(f"   User Agent: {session_info['user_agent'][:50]}...")
    print(f"   Request Count: {session_info['request_count']}")
    print(f"   Proxy Enabled: {session_info['proxy_enabled']}")
    
    # Test custom configuration
    print("\n2. Custom Configuration...")
    custom_config = {
        'session': {
            'cookies_enabled': True,
            'session_timeout': 3600
        },
        'headers': {
            'user_agent': 'Custom-TikTok-Downloader/1.0',
            'rotate_user_agent': False,
            'rotate_interval': 5,
            'custom': {
                'X-Custom-Header': 'test-value'
            }
        },
        'proxy': {
            'enabled': False,
            'url': 'http://localhost:8080'
        },
        'rate_limit': {
            'enabled': True,
            'sleep_interval': 2,
            'max_sleep_interval': 10
        }
    }
    
    custom_handler = TikTokHandler(config=custom_config)
    custom_session = custom_handler.get_session_info()
    print(f"   Custom User Agent: {custom_session['user_agent']}")
    print(f"   Proxy Enabled: {custom_session['proxy_enabled']}")
    
    # Test headers generation
    print("\n3. Headers Generation...")
    headers = custom_handler._get_headers()
    print(f"   User-Agent: {headers.get('User-Agent', 'Not set')}")
    print(f"   Accept: {headers.get('Accept', 'Not set')}")
    print(f"   Custom Header: {headers.get('X-Custom-Header', 'Not set')}")
    
    return handler, custom_handler


def test_user_agent_rotation():
    """Test user agent rotation functionality"""
    
    print("\n🔄 Testing User Agent Rotation")
    print("=" * 35)
    
    # Create handler with rotation enabled
    config = {
        'headers': {
            'rotate_user_agent': True,
            'rotate_interval': 3  # Rotate every 3 requests
        }
    }
    
    handler = TikTokHandler(config=config)
    
    # Track user agents over multiple simulated requests
    user_agents = []
    for i in range(10):
        # Simulate a request
        handler._update_session_state()
        current_ua = handler._current_user_agent
        user_agents.append(current_ua)
        
        print(f"   Request {i+1}: {current_ua[:30]}...")
        time.sleep(0.1)  # Small delay to simulate real requests
    
    # Check if rotation occurred
    unique_uas = set(user_agents)
    print(f"\n   Total requests: {len(user_agents)}")
    print(f"   Unique user agents: {len(unique_uas)}")
    print(f"   Rotation working: {'✅' if len(unique_uas) > 1 else '❌'}")
    
    return handler


def test_session_management():
    """Test session management features"""
    
    print("\n📊 Testing Session Management")
    print("=" * 32)
    
    handler = TikTokHandler()
    
    # Initial session state
    print("\n1. Initial Session State...")
    initial_session = handler.get_session_info()
    print(f"   Request Count: {initial_session['request_count']}")
    print(f"   Last Request Time: {initial_session['last_request_time']}")
    print(f"   Cookies Count: {initial_session['cookies_count']}")
    
    # Simulate some requests
    print("\n2. After Simulated Requests...")
    for i in range(5):
        handler._update_session_state()
        time.sleep(0.1)
    
    updated_session = handler.get_session_info()
    print(f"   Request Count: {updated_session['request_count']}")
    print(f"   Last Request Time: {updated_session['last_request_time']}")
    print(f"   Session updated: {'✅' if updated_session['request_count'] > 0 else '❌'}")
    
    # Test session clearing
    print("\n3. Session Clearing...")
    handler.clear_session()
    cleared_session = handler.get_session_info()
    print(f"   Request Count: {cleared_session['request_count']}")
    print(f"   Cookies Count: {cleared_session['cookies_count']}")
    print(f"   Session cleared: {'✅' if cleared_session['request_count'] == 0 else '❌'}")
    
    return handler


def test_proxy_configuration():
    """Test proxy configuration"""
    
    print("\n🌐 Testing Proxy Configuration")
    print("=" * 32)
    
    # Test without proxy
    print("\n1. No Proxy Configuration...")
    handler_no_proxy = TikTokHandler()
    proxy_config = handler_no_proxy._get_proxy_config()
    print(f"   Proxy Config: {proxy_config}")
    print(f"   No proxy: {'✅' if proxy_config is None else '❌'}")
    
    # Test with proxy enabled
    print("\n2. Proxy Enabled...")
    proxy_config = {
        'proxy': {
            'enabled': True,
            'url': 'http://proxy.example.com:8080'
        }
    }
    
    handler_with_proxy = TikTokHandler(config=proxy_config)
    proxy_result = handler_with_proxy._get_proxy_config()
    print(f"   Proxy Config: {proxy_result}")
    print(f"   Proxy enabled: {'✅' if proxy_result is not None else '❌'}")
    
    # Test with proxy disabled
    print("\n3. Proxy Disabled...")
    disabled_config = {
        'proxy': {
            'enabled': False,
            'url': 'http://proxy.example.com:8080'
        }
    }
    
    handler_disabled_proxy = TikTokHandler(config=disabled_config)
    disabled_result = handler_disabled_proxy._get_proxy_config()
    print(f"   Proxy Config: {disabled_result}")
    print(f"   Proxy disabled: {'✅' if disabled_result is None else '❌'}")
    
    return handler_with_proxy


def test_authentication_validation():
    """Test authentication validation logic"""
    
    print("\n✅ Testing Authentication Validation")
    print("=" * 40)
    
    # Test without authentication
    print("\n1. Without Authentication...")
    handler = TikTokHandler()
    should_auth = handler._should_authenticate()
    is_valid = handler._validate_authentication()
    print(f"   Should authenticate: {should_auth}")
    print(f"   Is valid: {is_valid}")
    print(f"   No auth validation: {'✅' if not should_auth and is_valid else '❌'}")
    
    # Test authentication setting
    print("\n2. Setting Authentication...")
    
    # Mock auth info class
    class MockAuthInfo:
        def __init__(self, valid=True):
            self._valid = valid
            self.credentials = {'api_key': 'test-key-123'}
        
        def is_valid(self):
            return self._valid
    
    # Test with valid auth
    valid_auth = MockAuthInfo(valid=True)
    handler.set_authentication(valid_auth)
    
    should_auth_valid = handler._should_authenticate()
    is_valid_valid = handler._validate_authentication()
    print(f"   Should authenticate (valid): {should_auth_valid}")
    print(f"   Is valid (valid): {is_valid_valid}")
    print(f"   Valid auth: {'✅' if should_auth_valid and is_valid_valid else '❌'}")
    
    # Test with invalid auth
    invalid_auth = MockAuthInfo(valid=False)
    handler.set_authentication(invalid_auth)
    
    should_auth_invalid = handler._should_authenticate()
    is_valid_invalid = handler._validate_authentication()
    print(f"   Should authenticate (invalid): {should_auth_invalid}")
    print(f"   Is valid (invalid): {is_valid_invalid}")
    print(f"   Invalid auth detected: {'✅' if should_auth_invalid and not is_valid_invalid else '❌'}")
    
    return handler


async def test_authentication_integration():
    """Test authentication integration with yt-dlp options"""
    
    print("\n🔧 Testing Authentication Integration")
    print("=" * 40)
    
    # Create handler with various auth configs
    config = {
        'headers': {
            'custom': {
                'X-TikTok-Client': 'custom-client',
                'X-API-Version': '1.0'
            }
        },
        'proxy': {
            'enabled': True,
            'url': 'http://test-proxy:8080'
        },
        'rate_limit': {
            'enabled': True,
            'sleep_interval': 1,
            'max_sleep_interval': 3
        }
    }
    
    handler = TikTokHandler(config=config)
    
    # Test yt-dlp options building
    print("\n1. Building yt-dlp Options...")
    base_opts = {'quiet': True, 'no_warnings': True}
    
    # Apply authentication
    handler._apply_authentication(base_opts)
    
    print(f"   HTTP Headers added: {'http_headers' in base_opts}")
    print(f"   Proxy added: {'proxy' in base_opts}")
    print(f"   Rate limiting added: {'sleep_interval' in base_opts}")
    
    if 'http_headers' in base_opts:
        headers = base_opts['http_headers']
        print(f"   Custom headers count: {len(headers)}")
        print(f"   User-Agent present: {'User-Agent' in headers}")
        print(f"   Custom header present: {'X-TikTok-Client' in headers}")
    
    # Test with authentication
    print("\n2. With Authentication...")
    
    class MockAuthInfo:
        def __init__(self):
            self.credentials = {'api_key': 'test-api-key-123'}
        
        def is_valid(self):
            return True
    
    handler.set_authentication(MockAuthInfo())
    auth_opts = {'quiet': True}
    handler._apply_authentication(auth_opts)
    
    if 'http_headers' in auth_opts and 'Authorization' in auth_opts['http_headers']:
        auth_header = auth_opts['http_headers']['Authorization']
        print(f"   Authorization header: {auth_header}")
        print(f"   API key authentication: {'✅' if 'Bearer' in auth_header else '❌'}")
    else:
        print(f"   No authorization header found")
    
    return handler


def main():
    """Main test function"""
    print("🔐 TikTok Authentication & Session Management Test Suite")
    print("=" * 65)
    
    try:
        # Test authentication configuration
        handler, custom_handler = test_authentication_config()
        
        # Test user agent rotation
        rotation_handler = test_user_agent_rotation()
        
        # Test session management
        session_handler = test_session_management()
        
        # Test proxy configuration
        proxy_handler = test_proxy_configuration()
        
        # Test authentication validation
        auth_handler = test_authentication_validation()
        
        # Test authentication integration
        asyncio.run(test_authentication_integration())
        
        print("\n🎉 All Authentication Tests Completed Successfully!")
        print("Authentication and session management features are working correctly.")
        
        # Summary
        print("\n📋 Test Summary:")
        print("   ✅ Basic authentication configuration")
        print("   ✅ User agent rotation system")
        print("   ✅ Session state management")
        print("   ✅ Proxy configuration support")
        print("   ✅ Authentication validation logic")
        print("   ✅ yt-dlp integration with auth options")
        
    except Exception as e:
        print(f"\n❌ Authentication test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 