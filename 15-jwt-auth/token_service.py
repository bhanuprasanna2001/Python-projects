"""
JWT Token Service
=================
Complete JWT token generation and validation service.
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import secrets
import hashlib


# =============================================================================
# Configuration
# =============================================================================

class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass
class TokenConfig:
    """JWT configuration."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    issuer: str = "my-app"
    audience: str = "my-app-users"


# Default config (use env vars in production!)
DEFAULT_CONFIG = TokenConfig(
    secret_key=secrets.token_hex(32),  # Generate random secret
    algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7,
)


# =============================================================================
# Token Service
# =============================================================================

class TokenService:
    """
    Service for JWT token generation and validation.
    """
    
    def __init__(self, config: TokenConfig = DEFAULT_CONFIG):
        self.config = config
    
    def create_access_token(
        self,
        user_id: str,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an access token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)
        
        payload = {
            # Standard claims
            "sub": user_id,  # Subject (user identifier)
            "iat": now,      # Issued at
            "exp": expire,   # Expiration
            "nbf": now,      # Not before
            "iss": self.config.issuer,    # Issuer
            "aud": self.config.audience,  # Audience
            
            # Custom claims
            "type": TokenType.ACCESS.value,
            "jti": secrets.token_hex(16),  # JWT ID (unique identifier)
        }
        
        if extra_claims:
            payload.update(extra_claims)
        
        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )
    
    def create_refresh_token(
        self,
        user_id: str,
        device_id: Optional[str] = None
    ) -> str:
        """Create a refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.config.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "type": TokenType.REFRESH.value,
            "jti": secrets.token_hex(16),
        }
        
        if device_id:
            payload["device_id"] = device_id
        
        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )
    
    def create_token_pair(
        self,
        user_id: str,
        extra_claims: Optional[Dict[str, Any]] = None,
        device_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create both access and refresh tokens."""
        access_token = self.create_access_token(user_id, extra_claims)
        refresh_token = self.create_refresh_token(user_id, device_id)
        return access_token, refresh_token
    
    def decode_token(
        self,
        token: str,
        verify_exp: bool = True,
        expected_type: Optional[TokenType] = None
    ) -> Dict[str, Any]:
        """
        Decode and validate a token.
        
        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid
            ValueError: Token type mismatch
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                options={
                    "verify_exp": verify_exp,
                    "require": ["sub", "iat", "exp", "type"],
                },
                issuer=self.config.issuer,
                audience=self.config.audience,
            )
            
            # Verify token type if specified
            if expected_type:
                token_type = payload.get("type")
                if token_type != expected_type.value:
                    raise ValueError(f"Expected {expected_type.value} token, got {token_type}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {e}")
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify an access token and return payload."""
        return self.decode_token(token, expected_type=TokenType.ACCESS)
    
    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Verify a refresh token and return payload."""
        return self.decode_token(token, expected_type=TokenType.REFRESH)
    
    def refresh_access_token(
        self,
        refresh_token: str,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Use refresh token to create new access token."""
        payload = self.verify_refresh_token(refresh_token)
        user_id = payload["sub"]
        return self.create_access_token(user_id, extra_claims)
    
    def get_token_id(self, token: str) -> Optional[str]:
        """Extract JTI (token ID) from token without full validation."""
        try:
            # Decode without verification to get JTI
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            return payload.get("jti")
        except Exception:
            return None
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Extract expiry time from token."""
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=timezone.utc)
            return None
        except Exception:
            return None


# =============================================================================
# Token Blacklist (for revocation)
# =============================================================================

class TokenBlacklist:
    """
    In-memory token blacklist.
    In production, use Redis or database.
    """
    
    def __init__(self):
        self._blacklist: Dict[str, datetime] = {}
    
    def add(self, jti: str, expiry: datetime) -> None:
        """Add token to blacklist."""
        self._blacklist[jti] = expiry
    
    def is_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        return jti in self._blacklist
    
    def cleanup(self) -> int:
        """Remove expired entries from blacklist."""
        now = datetime.now(timezone.utc)
        expired = [jti for jti, exp in self._blacklist.items() if exp < now]
        for jti in expired:
            del self._blacklist[jti]
        return len(expired)


# =============================================================================
# Extended Token Service with Revocation
# =============================================================================

class ExtendedTokenService(TokenService):
    """Token service with revocation support."""
    
    def __init__(self, config: TokenConfig = DEFAULT_CONFIG):
        super().__init__(config)
        self.blacklist = TokenBlacklist()
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding to blacklist."""
        jti = self.get_token_id(token)
        expiry = self.get_token_expiry(token)
        
        if jti and expiry:
            self.blacklist.add(jti, expiry)
            return True
        return False
    
    def is_token_revoked(self, token: str) -> bool:
        """Check if token has been revoked."""
        jti = self.get_token_id(token)
        return jti is not None and self.blacklist.is_blacklisted(jti)
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify access token including revocation check."""
        if self.is_token_revoked(token):
            raise jwt.InvalidTokenError("Token has been revoked")
        return super().verify_access_token(token)


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("JWT Token Service Demo")
    print("=" * 60)
    
    # Create service
    service = ExtendedTokenService()
    
    # Create tokens
    print("\n=== Creating Tokens ===\n")
    
    access_token, refresh_token = service.create_token_pair(
        user_id="user123",
        extra_claims={"role": "admin", "permissions": ["read", "write"]},
        device_id="device-abc"
    )
    
    print(f"Access Token:\n{access_token[:50]}...\n")
    print(f"Refresh Token:\n{refresh_token[:50]}...\n")
    
    # Verify access token
    print("=== Verifying Access Token ===\n")
    
    try:
        payload = service.verify_access_token(access_token)
        print(f"User ID: {payload['sub']}")
        print(f"Role: {payload.get('role')}")
        print(f"Permissions: {payload.get('permissions')}")
        print(f"Expires: {datetime.fromtimestamp(payload['exp'], tz=timezone.utc)}")
    except Exception as e:
        print(f"Verification failed: {e}")
    
    # Refresh token
    print("\n=== Refreshing Access Token ===\n")
    
    new_access_token = service.refresh_access_token(refresh_token)
    print(f"New Access Token:\n{new_access_token[:50]}...\n")
    
    # Revoke token
    print("=== Revoking Token ===\n")
    
    service.revoke_token(access_token)
    print("Token revoked")
    
    try:
        service.verify_access_token(access_token)
    except Exception as e:
        print(f"Verification after revocation: {e}")
    
    print("\n" + "=" * 60)
