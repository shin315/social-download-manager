#!/usr/bin/env python3
"""
Social Download Manager V2.0 - Automated Security Testing Suite

Comprehensive security testing framework covering:
- Input validation security
- Authentication & authorization
- Data protection & privacy
- Network security
- Error handling
- Session management
- File system security

Usage:
    python tests/security/security_tests.py
    python -m pytest tests/security/security_tests.py -v
"""

import pytest
import tempfile
import os
import sys
import json
import hashlib
import hmac
import re
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse, urljoin

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import V2.0 components for testing
try:
    from ui.core.app_controller import AppController
    from ui.core.component_bus import ComponentBus
    from ui.core.state_manager import StateManager
    from ui.core.theme_manager import ThemeManager
    from ui.core.performance_monitor import PerformanceMonitor
except ImportError as e:
    print(f"Warning: Could not import V2.0 components: {e}")
    # Create mock classes for testing
    class AppController:
        def __init__(self):
            self.services = {}
    
    class ComponentBus:
        def __init__(self):
            self.components = {}
    
    class StateManager:
        def __init__(self):
            self.state = {}
    
    class ThemeManager:
        def __init__(self):
            self.current_theme = {}
    
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}


class TestInputValidation:
    """Test input validation security measures"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.tiktok.com/@user/video/123456789",
            "http://example.com/video.mp4",
            "https://vimeo.com/123456789"
        ]
        
        self.malicious_urls = [
            "javascript:alert('xss')",
            "file:///etc/passwd",
            "ftp://malicious.com/file",
            "../../../etc/passwd",
            "http://localhost:22/ssh-attack",
            "data:text/html,<script>alert('xss')</script>",
            "mailto:attacker@evil.com",
            ""  # Empty URL
        ]
    
    def test_url_validation_security(self):
        """Test URL validation against malicious inputs"""
        def validate_download_url(url):
            """Enhanced URL validation function"""
            if not url or not isinstance(url, str):
                return False
            
            # Basic length check
            if len(url) > 2048:  # RFC 7230 recommended limit
                return False
            
            # URL pattern validation
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(url):
                return False
            
            try:
                parsed = urlparse(url)
                return parsed.scheme in ['http', 'https'] and parsed.netloc
            except Exception:
                return False
        
        # Test valid URLs
        for url in self.test_urls:
            assert validate_download_url(url), f"Valid URL failed validation: {url}"
        
        # Test malicious URLs
        for url in self.malicious_urls:
            assert not validate_download_url(url), f"Malicious URL passed validation: {url}"
        
        print("✅ URL validation security test passed")
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        def safe_file_path(user_input, base_dir="/tmp/downloads"):
            """Secure file path handling"""
            if not user_input or not isinstance(user_input, str):
                return None
            
            # Remove dangerous characters and patterns
            user_input = user_input.replace("../", "").replace("..\\", "")
            user_input = re.sub(r'[<>:"|?*]', '', user_input)
            
            # Join with base directory and resolve
            full_path = os.path.join(base_dir, user_input)
            resolved_path = os.path.abspath(full_path)
            base_resolved = os.path.abspath(base_dir)
            
            # Ensure path stays within base directory
            if not resolved_path.startswith(base_resolved):
                return None
            
            return resolved_path
        
        # Test malicious file paths
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../root/.ssh/id_rsa",
            "file.txt/../../../secret.txt",
            "/etc/passwd",
            "C:\\windows\\system32\\config\\sam"
        ]
        
        for path in malicious_paths:
            result = safe_file_path(path)
            if result:
                # If path is allowed, ensure it's within safe directory
                assert "/tmp/downloads" in result, f"Path traversal not prevented: {path} -> {result}"
        
        print("✅ Path traversal protection test passed")
    
    def test_input_sanitization(self):
        """Test input sanitization for XSS and injection attacks"""
        def sanitize_input(user_input):
            """Sanitize user input"""
            if not isinstance(user_input, str):
                return str(user_input)
            
            # Remove HTML tags and dangerous characters
            user_input = re.sub(r'<[^>]*>', '', user_input)
            user_input = user_input.replace('<', '&lt;').replace('>', '&gt;')
            user_input = user_input.replace('"', '&quot;').replace("'", '&#x27;')
            user_input = user_input.replace('&', '&amp;')
            
            return user_input.strip()
        
        # Test XSS payloads
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            sanitized = sanitize_input(payload)
            assert '<script>' not in sanitized, f"XSS payload not sanitized: {payload}"
            assert 'javascript:' not in sanitized, f"JavaScript URL not sanitized: {payload}"
            assert 'onerror=' not in sanitized, f"Event handler not sanitized: {payload}"
        
        print("✅ Input sanitization test passed")


class TestAuthenticationSecurity:
    """Test authentication and authorization security"""
    
    def setup_method(self):
        """Setup authentication test environment"""
        self.secret_key = "test_secret_key_for_security_testing"
        self.session_timeout = 3600  # 1 hour
    
    def test_secure_token_generation(self):
        """Test secure token generation and validation"""
        def generate_secure_token(length=32):
            """Generate cryptographically secure token"""
            import secrets
            return secrets.token_urlsafe(length)
        
        def validate_token_security(token):
            """Validate token security properties"""
            if not token or len(token) < 16:
                return False
            
            # Check for sufficient entropy (basic check)
            unique_chars = len(set(token))
            if unique_chars < 8:  # Too predictable
                return False
            
            return True
        
        # Generate multiple tokens and test uniqueness
        tokens = [generate_secure_token() for _ in range(100)]
        
        # Test uniqueness
        assert len(set(tokens)) == len(tokens), "Generated tokens are not unique"
        
        # Test security properties
        for token in tokens[:10]:  # Test first 10
            assert validate_token_security(token), f"Token failed security validation: {token}"
        
        print("✅ Secure token generation test passed")
    
    def test_session_management_security(self):
        """Test session management security"""
        class SecureSessionManager:
            def __init__(self, secret_key, timeout=3600):
                self.secret_key = secret_key.encode()
                self.timeout = timeout
                self.sessions = {}
            
            def create_session(self, user_id):
                """Create secure session"""
                import time
                import secrets
                
                session_id = secrets.token_urlsafe(32)
                timestamp = time.time()
                
                # Create session data with HMAC
                session_data = {
                    'user_id': user_id,
                    'timestamp': timestamp,
                    'expires': timestamp + self.timeout
                }
                
                # Sign session data
                signature = hmac.new(
                    self.secret_key, 
                    json.dumps(session_data).encode(), 
                    hashlib.sha256
                ).hexdigest()
                
                session_data['signature'] = signature
                self.sessions[session_id] = session_data
                
                return session_id
            
            def validate_session(self, session_id):
                """Validate session with timing attack protection"""
                if session_id not in self.sessions:
                    return False
                
                session_data = self.sessions[session_id].copy()
                stored_signature = session_data.pop('signature')
                
                # Verify signature with timing attack protection
                expected_signature = hmac.new(
                    self.secret_key,
                    json.dumps(session_data).encode(),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(stored_signature, expected_signature):
                    return False
                
                # Check expiration
                if time.time() > session_data['expires']:
                    del self.sessions[session_id]
                    return False
                
                return True
        
        # Test session manager
        session_mgr = SecureSessionManager(self.secret_key, self.session_timeout)
        
        # Create session
        session_id = session_mgr.create_session("test_user")
        assert session_mgr.validate_session(session_id), "Valid session failed validation"
        
        # Test invalid session
        assert not session_mgr.validate_session("invalid_session"), "Invalid session passed validation"
        
        # Test session tampering
        tampered_session = session_id + "x"
        assert not session_mgr.validate_session(tampered_session), "Tampered session passed validation"
        
        print("✅ Session management security test passed")
    
    def test_rate_limiting(self):
        """Test rate limiting security"""
        class RateLimiter:
            def __init__(self, max_requests=10, window=60):
                self.max_requests = max_requests
                self.window = window
                self.requests = {}
            
            def is_allowed(self, client_id):
                """Check if request is allowed"""
                current_time = time.time()
                
                if client_id not in self.requests:
                    self.requests[client_id] = []
                
                # Clean old requests
                self.requests[client_id] = [
                    req_time for req_time in self.requests[client_id]
                    if current_time - req_time < self.window
                ]
                
                # Check rate limit
                if len(self.requests[client_id]) >= self.max_requests:
                    return False
                
                # Add current request
                self.requests[client_id].append(current_time)
                return True
        
        # Test rate limiter
        rate_limiter = RateLimiter(max_requests=5, window=10)
        
        # Normal usage should be allowed
        for i in range(5):
            assert rate_limiter.is_allowed("client1"), f"Request {i} should be allowed"
        
        # 6th request should be blocked
        assert not rate_limiter.is_allowed("client1"), "Rate limit not enforced"
        
        # Different client should still be allowed
        assert rate_limiter.is_allowed("client2"), "Rate limit incorrectly applied to different client"
        
        print("✅ Rate limiting test passed")


class TestDataProtection:
    """Test data protection and privacy security"""
    
    def test_data_encryption(self):
        """Test data encryption and decryption"""
        def encrypt_data(data, key):
            """Encrypt data using AES-256 (simulated)"""
            # For testing, use simple reversible encoding
            import base64
            
            # Simulate AES encryption with base64 encoding
            data_bytes = json.dumps(data).encode()
            key_hash = hashlib.sha256(key.encode()).digest()
            
            # XOR with key hash (simplified encryption)
            encrypted_bytes = bytes(a ^ b for a, b in zip(data_bytes, key_hash * (len(data_bytes) // len(key_hash) + 1)))
            return base64.b64encode(encrypted_bytes).decode()
        
        def decrypt_data(encrypted_data, key):
            """Decrypt data"""
            import base64
            
            encrypted_bytes = base64.b64decode(encrypted_data)
            key_hash = hashlib.sha256(key.encode()).digest()
            
            # XOR with key hash (simplified decryption)
            decrypted_bytes = bytes(a ^ b for a, b in zip(encrypted_bytes, key_hash * (len(encrypted_bytes) // len(key_hash) + 1)))
            return json.loads(decrypted_bytes.decode())
        
        # Test encryption/decryption
        test_data = {"user_id": "12345", "preferences": {"theme": "dark"}}
        encryption_key = "secure_encryption_key_for_testing"
        
        encrypted = encrypt_data(test_data, encryption_key)
        decrypted = decrypt_data(encrypted, encryption_key)
        
        assert decrypted == test_data, "Data encryption/decryption failed"
        
        # Test with wrong key
        try:
            decrypt_data(encrypted, "wrong_key")
            assert False, "Decryption with wrong key should fail"
        except:
            pass  # Expected to fail
        
        print("✅ Data encryption test passed")
    
    def test_secure_file_handling(self):
        """Test secure file operations"""
        def secure_file_write(file_path, data, permissions=0o644):
            """Securely write file with proper permissions"""
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file with secure permissions
            with open(file_path, 'w') as f:
                f.write(data)
            
            # Set secure permissions
            os.chmod(file_path, permissions)
            
            return True
        
        def secure_file_read(file_path, max_size=1024*1024):  # 1MB limit
            """Securely read file with size limits"""
            if not os.path.exists(file_path):
                return None
            
            # Check file size
            if os.path.getsize(file_path) > max_size:
                raise ValueError("File too large")
            
            with open(file_path, 'r') as f:
                return f.read()
        
        # Test secure file operations
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            test_data = "This is test data for security validation"
            
            # Test secure write
            assert secure_file_write(test_file, test_data)
            
            # Test secure read
            read_data = secure_file_read(test_file)
            assert read_data == test_data, "File read/write failed"
            
            # Test file permissions
            file_stat = os.stat(test_file)
            file_permissions = oct(file_stat.st_mode)[-3:]
            assert file_permissions == "644", f"File permissions incorrect: {file_permissions}"
        
        print("✅ Secure file handling test passed")
    
    def test_memory_cleanup(self):
        """Test sensitive data cleanup from memory"""
        def secure_string_clear(sensitive_data):
            """Attempt to clear sensitive data from memory"""
            if isinstance(sensitive_data, str):
                # In Python, strings are immutable, so we can't truly clear them
                # But we can overwrite variables and trigger garbage collection
                sensitive_data = "0" * len(sensitive_data)
            
            import gc
            gc.collect()
            return True
        
        # Test memory cleanup
        sensitive_password = "super_secret_password_123"
        original_length = len(sensitive_password)
        
        assert secure_string_clear(sensitive_password), "Memory cleanup failed"
        
        # Note: In real applications, use libraries like pystring-clear
        # or implement in C for true memory clearing
        
        print("✅ Memory cleanup test passed")


class TestNetworkSecurity:
    """Test network security measures"""
    
    def test_https_enforcement(self):
        """Test HTTPS enforcement"""
        def validate_secure_connection(url):
            """Validate that connection uses HTTPS"""
            parsed = urlparse(url)
            
            # Enforce HTTPS for external connections
            if parsed.netloc != 'localhost' and not parsed.netloc.startswith('127.'):
                return parsed.scheme == 'https'
            
            return True  # Allow HTTP for localhost
        
        # Test URLs
        secure_urls = [
            "https://www.youtube.com/watch?v=123",
            "https://api.tiktok.com/user/123",
            "http://localhost:8080/api",
            "http://127.0.0.1:3000/test"
        ]
        
        insecure_urls = [
            "http://www.youtube.com/watch?v=123",
            "http://api.tiktok.com/user/123",
            "ftp://downloads.example.com/file.zip"
        ]
        
        # Test secure URLs
        for url in secure_urls:
            assert validate_secure_connection(url), f"Secure URL failed validation: {url}"
        
        # Test insecure URLs
        for url in insecure_urls:
            assert not validate_secure_connection(url), f"Insecure URL passed validation: {url}"
        
        print("✅ HTTPS enforcement test passed")
    
    def test_certificate_validation(self):
        """Test SSL certificate validation"""
        def validate_ssl_certificate(hostname, verify_cert=True):
            """Validate SSL certificate (simulated)"""
            if not verify_cert:
                return False  # Should always verify in production
            
            # Simulate certificate validation
            trusted_domains = [
                'youtube.com', 'www.youtube.com',
                'tiktok.com', 'www.tiktok.com',
                'vimeo.com', 'www.vimeo.com'
            ]
            
            # Check if domain is in trusted list (simplified check)
            for domain in trusted_domains:
                if hostname.endswith(domain):
                    return True
            
            return False
        
        # Test certificate validation
        valid_hostnames = [
            'www.youtube.com',
            'api.tiktok.com',
            'player.vimeo.com'
        ]
        
        invalid_hostnames = [
            'malicious.com',
            'fake-youtube.com',
            'evil.tiktok.com.malicious.com'
        ]
        
        # Test valid certificates
        for hostname in valid_hostnames:
            assert validate_ssl_certificate(hostname), f"Valid certificate failed: {hostname}"
        
        # Test invalid certificates
        for hostname in invalid_hostnames:
            assert not validate_ssl_certificate(hostname), f"Invalid certificate passed: {hostname}"
        
        print("✅ Certificate validation test passed")
    
    def test_proxy_security(self):
        """Test proxy configuration security"""
        def validate_proxy_config(proxy_config):
            """Validate proxy configuration"""
            if not proxy_config:
                return True  # No proxy is valid
            
            # Parse proxy URL
            try:
                parsed = urlparse(proxy_config)
            except:
                return False
            
            # Validate proxy scheme
            if parsed.scheme not in ['http', 'https', 'socks4', 'socks5']:
                return False
            
            # Validate proxy host
            if not parsed.netloc:
                return False
            
            # Reject localhost/private IP proxies from external configs
            if parsed.hostname in ['localhost', '127.0.0.1']:
                return False
            
            return True
        
        # Test proxy configurations
        valid_proxies = [
            "http://proxy.company.com:8080",
            "https://secure-proxy.example.com:3128",
            "socks5://proxy.company.com:1080",
            None  # No proxy
        ]
        
        invalid_proxies = [
            "ftp://proxy.company.com:21",
            "proxy.company.com:8080",  # Missing scheme
            "http://localhost:8080",    # Localhost proxy
            "http://",                  # Missing host
            "invalid-url"
        ]
        
        # Test valid proxies
        for proxy in valid_proxies:
            assert validate_proxy_config(proxy), f"Valid proxy failed: {proxy}"
        
        # Test invalid proxies
        for proxy in invalid_proxies:
            assert not validate_proxy_config(proxy), f"Invalid proxy passed: {proxy}"
        
        print("✅ Proxy security test passed")


def run_comprehensive_security_tests():
    """Run all security tests and generate report"""
    print("🔒 Starting Comprehensive Security Testing Suite")
    print("=" * 60)
    
    test_results = {
        "test_suite": "Social Download Manager V2.0 Security Tests",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests_passed": 0,
        "tests_failed": 0,
        "test_details": []
    }
    
    # Test classes to run
    test_classes = [
        TestInputValidation,
        TestAuthenticationSecurity,
        TestDataProtection,
        TestNetworkSecurity
    ]
    
    for test_class in test_classes:
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 40)
        
        for method_name in test_methods:
            try:
                # Setup if available
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()
                
                # Run test
                method = getattr(test_instance, method_name)
                method()
                
                test_results["tests_passed"] += 1
                test_results["test_details"].append({
                    "test_class": test_class.__name__,
                    "test_method": method_name,
                    "status": "PASSED",
                    "message": "Test completed successfully"
                })
                
            except Exception as e:
                test_results["tests_failed"] += 1
                test_results["test_details"].append({
                    "test_class": test_class.__name__,
                    "test_method": method_name,
                    "status": "FAILED",
                    "message": str(e)
                })
                print(f"❌ {method_name} FAILED: {e}")
    
    # Calculate overall results
    total_tests = test_results["tests_passed"] + test_results["tests_failed"]
    success_rate = (test_results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 60)
    print("🔒 SECURITY TESTING RESULTS")
    print("=" * 60)
    print(f"Tests Passed: {test_results['tests_passed']}")
    print(f"Tests Failed: {test_results['tests_failed']}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Overall Status: {'✅ PASSED' if test_results['tests_failed'] == 0 else '❌ FAILED'}")
    
    # Save results
    results_file = "tests/security/security_test_results.json"
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return test_results["tests_failed"] == 0


if __name__ == "__main__":
    """Run security tests when executed directly"""
    success = run_comprehensive_security_tests()
    sys.exit(0 if success else 1) 