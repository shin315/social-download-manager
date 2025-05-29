"""
Authentication framework for platform handlers

This module provides a flexible authentication system supporting various
authentication methods including OAuth, API keys, JWT tokens, and session-based auth.
Includes token refresh, secure credential storage, and extensible platform-specific auth.
"""

import asyncio
import json
import logging
import hashlib
import secrets
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse
import base64

from .enums import AuthType, PlatformType
from .models import AuthenticationInfo

logger = logging.getLogger(__name__)


# =====================================================
# Authentication Exceptions
# =====================================================

class AuthenticationError(Exception):
    """Base authentication error"""
    
    def __init__(self, message: str, auth_type: Optional[AuthType] = None, platform: Optional[PlatformType] = None):
        super().__init__(message)
        self.auth_type = auth_type
        self.platform = platform


class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided"""
    pass


class RefreshTokenError(AuthenticationError):
    """Error refreshing token"""
    pass


class AuthFlowError(AuthenticationError):
    """Error in authentication flow"""
    pass


# =====================================================
# Credential Storage
# =====================================================

class CredentialStorage(ABC):
    """Abstract credential storage interface"""
    
    @abstractmethod
    async def store_credentials(self, key: str, credentials: Dict[str, Any]) -> None:
        """Store credentials securely"""
        pass
    
    @abstractmethod
    async def retrieve_credentials(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored credentials"""
        pass
    
    @abstractmethod
    async def delete_credentials(self, key: str) -> bool:
        """Delete stored credentials"""
        pass
    
    @abstractmethod
    async def list_stored_keys(self) -> List[str]:
        """List all stored credential keys"""
        pass


class InMemoryCredentialStorage(CredentialStorage):
    """Simple in-memory credential storage (not persistent)"""
    
    def __init__(self):
        self._credentials: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def store_credentials(self, key: str, credentials: Dict[str, Any]) -> None:
        async with self._lock:
            self._credentials[key] = credentials.copy()
            logger.debug(f"Stored credentials for key: {key}")
    
    async def retrieve_credentials(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._credentials.get(key)
    
    async def delete_credentials(self, key: str) -> bool:
        async with self._lock:
            if key in self._credentials:
                del self._credentials[key]
                logger.debug(f"Deleted credentials for key: {key}")
                return True
            return False
    
    async def list_stored_keys(self) -> List[str]:
        async with self._lock:
            return list(self._credentials.keys())


class FileCredentialStorage(CredentialStorage):
    """File-based credential storage with encryption"""
    
    def __init__(self, storage_path: Path, encryption_key: Optional[str] = None):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._encryption_key = encryption_key or self._generate_key()
        self._lock = asyncio.Lock()
    
    def _generate_key(self) -> str:
        """Generate a simple encryption key"""
        return secrets.token_hex(32)
    
    def _encrypt_data(self, data: str) -> str:
        """Simple XOR encryption (not for production)"""
        key_bytes = self._encryption_key.encode()
        data_bytes = data.encode()
        
        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Simple XOR decryption"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            key_bytes = self._encryption_key.encode()
            
            decrypted = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
            
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise AuthenticationError("Failed to decrypt stored credentials")
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for credential key"""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.storage_path / f"{safe_key}.cred"
    
    async def store_credentials(self, key: str, credentials: Dict[str, Any]) -> None:
        async with self._lock:
            try:
                file_path = self._get_file_path(key)
                data = json.dumps(credentials)
                encrypted_data = self._encrypt_data(data)
                
                with open(file_path, 'w') as f:
                    f.write(encrypted_data)
                
                logger.debug(f"Stored credentials to file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to store credentials: {e}")
                raise AuthenticationError(f"Failed to store credentials: {e}")
    
    async def retrieve_credentials(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            try:
                file_path = self._get_file_path(key)
                if not file_path.exists():
                    return None
                
                with open(file_path, 'r') as f:
                    encrypted_data = f.read()
                
                decrypted_data = self._decrypt_data(encrypted_data)
                return json.loads(decrypted_data)
            except Exception as e:
                logger.error(f"Failed to retrieve credentials: {e}")
                return None
    
    async def delete_credentials(self, key: str) -> bool:
        async with self._lock:
            try:
                file_path = self._get_file_path(key)
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Deleted credential file: {file_path}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to delete credentials: {e}")
                return False
    
    async def list_stored_keys(self) -> List[str]:
        async with self._lock:
            keys = []
            for file_path in self.storage_path.glob("*.cred"):
                try:
                    # In a real implementation, you'd need to store a mapping
                    # For now, just return the file stem
                    keys.append(file_path.stem)
                except Exception:
                    continue
            return keys


# =====================================================
# Token Management
# =====================================================

@dataclass
class Token:
    """Authentication token"""
    access_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    @property
    def expires_in_seconds(self) -> Optional[int]:
        """Get seconds until expiration"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now()
        return max(0, int(delta.total_seconds()))
    
    @property
    def authorization_header(self) -> str:
        """Get Authorization header value"""
        return f"{self.token_type} {self.access_token}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'access_token': self.access_token,
            'token_type': self.token_type,
            'scope': self.scope,
            **self.extra_data
        }
        
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        if self.refresh_token:
            data['refresh_token'] = self.refresh_token
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Token':
        """Create from dictionary"""
        expires_at = None
        if 'expires_at' in data:
            expires_at = datetime.fromisoformat(data['expires_at'])
        elif 'expires_in' in data:
            expires_at = datetime.now() + timedelta(seconds=int(data['expires_in']))
        
        return cls(
            access_token=data['access_token'],
            token_type=data.get('token_type', 'Bearer'),
            expires_at=expires_at,
            refresh_token=data.get('refresh_token'),
            scope=data.get('scope'),
            extra_data={k: v for k, v in data.items() if k not in {
                'access_token', 'token_type', 'expires_at', 'expires_in', 
                'refresh_token', 'scope'
            }}
        )


class TokenManager:
    """Manages authentication tokens with automatic refresh"""
    
    def __init__(self, storage: CredentialStorage):
        self._storage = storage
        self._tokens: Dict[str, Token] = {}
        self._refresh_callbacks: Dict[str, Callable[[Token], Token]] = {}
        self._lock = asyncio.Lock()
    
    async def store_token(self, key: str, token: Token) -> None:
        """Store token in memory and persistent storage"""
        async with self._lock:
            self._tokens[key] = token
            await self._storage.store_credentials(f"token_{key}", token.to_dict())
            logger.debug(f"Stored token for key: {key}")
    
    async def get_token(self, key: str, auto_refresh: bool = True) -> Optional[Token]:
        """Get token, automatically refreshing if needed"""
        async with self._lock:
            # Try memory first
            token = self._tokens.get(key)
            
            # Try storage if not in memory
            if not token:
                token_data = await self._storage.retrieve_credentials(f"token_{key}")
                if token_data:
                    token = Token.from_dict(token_data)
                    self._tokens[key] = token
            
            # Refresh if expired and auto_refresh is enabled
            if token and token.is_expired and auto_refresh:
                token = await self._refresh_token(key, token)
            
            return token
    
    async def delete_token(self, key: str) -> bool:
        """Delete token from memory and storage"""
        async with self._lock:
            deleted = False
            
            if key in self._tokens:
                del self._tokens[key]
                deleted = True
            
            storage_deleted = await self._storage.delete_credentials(f"token_{key}")
            return deleted or storage_deleted
    
    def set_refresh_callback(self, key: str, callback: Callable[[Token], Token]) -> None:
        """Set callback for token refresh"""
        self._refresh_callbacks[key] = callback
    
    async def _refresh_token(self, key: str, token: Token) -> Optional[Token]:
        """Refresh an expired token"""
        if not token.refresh_token:
            logger.warning(f"No refresh token available for key: {key}")
            return token
        
        callback = self._refresh_callbacks.get(key)
        if not callback:
            logger.warning(f"No refresh callback set for key: {key}")
            return token
        
        try:
            logger.info(f"Refreshing token for key: {key}")
            new_token = await callback(token)
            await self.store_token(key, new_token)
            return new_token
        except Exception as e:
            logger.error(f"Failed to refresh token for {key}: {e}")
            raise RefreshTokenError(f"Failed to refresh token: {e}")


# =====================================================
# Authentication Providers
# =====================================================

class AuthProvider(ABC):
    """Abstract authentication provider"""
    
    def __init__(self, platform_type: PlatformType, config: Dict[str, Any]):
        self.platform_type = platform_type
        self.config = config
        self._logger = logging.getLogger(f"auth.{platform_type.value}")
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationInfo:
        """Perform authentication and return auth info"""
        pass
    
    @abstractmethod
    async def refresh_token(self, auth_info: AuthenticationInfo) -> AuthenticationInfo:
        """Refresh authentication token"""
        pass
    
    @abstractmethod
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate credential format"""
        pass


class APIKeyAuthProvider(AuthProvider):
    """API Key authentication provider"""
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationInfo:
        api_key = credentials.get('api_key')
        if not api_key:
            raise InvalidCredentialsError("API key is required")
        
        return AuthenticationInfo(
            auth_type=AuthType.API_KEY,
            credentials={'api_key': api_key},
            token=api_key
        )
    
    async def refresh_token(self, auth_info: AuthenticationInfo) -> AuthenticationInfo:
        # API keys don't typically need refresh
        return auth_info
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        return 'api_key' in credentials and credentials['api_key']


class OAuthProvider(AuthProvider):
    """OAuth 2.0 authentication provider"""
    
    def __init__(self, platform_type: PlatformType, config: Dict[str, Any]):
        super().__init__(platform_type, config)
        self._client_id = config.get('client_id')
        self._client_secret = config.get('client_secret')
        self._redirect_uri = config.get('redirect_uri', 'http://localhost:8080/callback')
        self._auth_url = config.get('auth_url')
        self._token_url = config.get('token_url')
        self._scope = config.get('scope', '')
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth authorization URL"""
        if not self._auth_url:
            raise AuthFlowError("Authorization URL not configured")
        
        params = {
            'response_type': 'code',
            'client_id': self._client_id,
            'redirect_uri': self._redirect_uri,
            'scope': self._scope
        }
        
        if state:
            params['state'] = state
        
        return f"{self._auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str, state: Optional[str] = None) -> Token:
        """Exchange authorization code for access token"""
        if not self._token_url:
            raise AuthFlowError("Token URL not configured")
        
        # In a real implementation, you'd make an HTTP request here
        # For now, simulate token response
        return Token(
            access_token=f"oauth_token_{secrets.token_hex(16)}",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
            refresh_token=f"refresh_{secrets.token_hex(16)}",
            scope=self._scope
        )
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationInfo:
        code = credentials.get('code')
        if not code:
            raise InvalidCredentialsError("Authorization code is required")
        
        token = await self.exchange_code_for_token(code)
        
        return AuthenticationInfo(
            auth_type=AuthType.OAUTH,
            token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=token.expires_at,
            scope=token.scope.split() if token.scope else []
        )
    
    async def refresh_token(self, auth_info: AuthenticationInfo) -> AuthenticationInfo:
        if not auth_info.refresh_token:
            raise RefreshTokenError("No refresh token available")
        
        # In a real implementation, make HTTP request to refresh token
        # For now, simulate refresh
        new_token = Token(
            access_token=f"refreshed_token_{secrets.token_hex(16)}",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
            refresh_token=auth_info.refresh_token
        )
        
        return AuthenticationInfo(
            auth_type=AuthType.OAUTH,
            token=new_token.access_token,
            refresh_token=new_token.refresh_token,
            expires_at=new_token.expires_at,
            scope=auth_info.scope
        )
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        return 'code' in credentials or ('access_token' in credentials)


class SessionAuthProvider(AuthProvider):
    """Session-based authentication provider"""
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationInfo:
        username = credentials.get('username')
        password = credentials.get('password')
        
        if not username or not password:
            raise InvalidCredentialsError("Username and password are required")
        
        # In a real implementation, you'd validate credentials
        # For now, simulate session creation
        session_token = f"session_{secrets.token_hex(16)}"
        
        return AuthenticationInfo(
            auth_type=AuthType.SESSION,
            credentials={'username': username},
            token=session_token,
            expires_at=datetime.now() + timedelta(days=7)
        )
    
    async def refresh_token(self, auth_info: AuthenticationInfo) -> AuthenticationInfo:
        # Extend session
        return AuthenticationInfo(
            auth_type=auth_info.auth_type,
            credentials=auth_info.credentials,
            token=auth_info.token,
            expires_at=datetime.now() + timedelta(days=7),
            scope=auth_info.scope
        )
    
    def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        return 'username' in credentials and 'password' in credentials


# =====================================================
# Authentication Manager
# =====================================================

class AuthenticationManager:
    """Central authentication manager"""
    
    def __init__(self, storage: Optional[CredentialStorage] = None):
        self._storage = storage or InMemoryCredentialStorage()
        self._token_manager = TokenManager(self._storage)
        self._providers: Dict[Tuple[PlatformType, AuthType], AuthProvider] = {}
        self._auth_cache: Dict[str, AuthenticationInfo] = {}
        self._lock = asyncio.Lock()
    
    def register_provider(
        self, 
        platform_type: PlatformType, 
        auth_type: AuthType, 
        provider: AuthProvider
    ) -> None:
        """Register an authentication provider"""
        key = (platform_type, auth_type)
        self._providers[key] = provider
        logger.info(f"Registered auth provider: {platform_type.value} + {auth_type.value}")
    
    def get_provider(
        self, 
        platform_type: PlatformType, 
        auth_type: AuthType
    ) -> Optional[AuthProvider]:
        """Get authentication provider"""
        return self._providers.get((platform_type, auth_type))
    
    async def authenticate(
        self,
        platform_type: PlatformType,
        auth_type: AuthType,
        credentials: Dict[str, Any],
        cache_key: Optional[str] = None
    ) -> AuthenticationInfo:
        """Perform authentication"""
        provider = self.get_provider(platform_type, auth_type)
        if not provider:
            raise AuthenticationError(
                f"No auth provider for {platform_type.value} + {auth_type.value}",
                auth_type=auth_type,
                platform=platform_type
            )
        
        if not provider.validate_credentials(credentials):
            raise InvalidCredentialsError("Invalid credential format")
        
        try:
            auth_info = await provider.authenticate(credentials)
            
            # Cache if cache_key provided
            if cache_key:
                await self._cache_auth_info(cache_key, auth_info)
            
            return auth_info
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Authentication failed: {e}")
    
    async def get_cached_auth(self, cache_key: str) -> Optional[AuthenticationInfo]:
        """Get cached authentication info"""
        async with self._lock:
            auth_info = self._auth_cache.get(cache_key)
            if auth_info and auth_info.is_expired:
                # Try to refresh
                try:
                    auth_info = await self._refresh_auth_info(cache_key, auth_info)
                except Exception as e:
                    logger.warning(f"Failed to refresh auth for {cache_key}: {e}")
                    return None
            
            return auth_info
    
    async def _cache_auth_info(self, cache_key: str, auth_info: AuthenticationInfo) -> None:
        """Cache authentication info"""
        async with self._lock:
            self._auth_cache[cache_key] = auth_info
            
            # Also store in persistent storage
            auth_data = {
                'auth_type': auth_info.auth_type.value,
                'credentials': auth_info.credentials,
                'token': auth_info.token,
                'refresh_token': auth_info.refresh_token,
                'expires_at': auth_info.expires_at.isoformat() if auth_info.expires_at else None,
                'scope': auth_info.scope
            }
            await self._storage.store_credentials(f"auth_{cache_key}", auth_data)
    
    async def _refresh_auth_info(
        self, 
        cache_key: str, 
        auth_info: AuthenticationInfo
    ) -> AuthenticationInfo:
        """Refresh authentication info"""
        # Find appropriate provider
        provider = None
        for (platform_type, auth_type), prov in self._providers.items():
            if auth_type == auth_info.auth_type:
                provider = prov
                break
        
        if not provider:
            raise RefreshTokenError("No provider available for refresh")
        
        refreshed_auth = await provider.refresh_token(auth_info)
        await self._cache_auth_info(cache_key, refreshed_auth)
        return refreshed_auth
    
    async def revoke_auth(self, cache_key: str) -> bool:
        """Revoke cached authentication"""
        async with self._lock:
            removed = False
            
            if cache_key in self._auth_cache:
                del self._auth_cache[cache_key]
                removed = True
            
            storage_removed = await self._storage.delete_credentials(f"auth_{cache_key}")
            return removed or storage_removed
    
    def get_supported_auth_types(self, platform_type: PlatformType) -> List[AuthType]:
        """Get supported auth types for platform"""
        return [
            auth_type for (ptype, auth_type) in self._providers.keys()
            if ptype == platform_type
        ] 