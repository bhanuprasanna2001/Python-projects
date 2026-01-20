"""
OAuth2 Implementation
=====================
OAuth2 flows with FastAPI and Authlib.
"""

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dataclasses import dataclass
import secrets
import hashlib
import base64
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta, timezone
import httpx


# =============================================================================
# OAuth2 Configuration
# =============================================================================

@dataclass
class OAuth2Config:
    """OAuth2 provider configuration."""
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    redirect_uri: str
    scope: str = "openid profile email"


# Example configurations (replace with real values)
GITHUB_CONFIG = OAuth2Config(
    client_id="your-github-client-id",
    client_secret="your-github-client-secret",
    authorize_url="https://github.com/login/oauth/authorize",
    token_url="https://github.com/login/oauth/access_token",
    userinfo_url="https://api.github.com/user",
    redirect_uri="http://localhost:8000/auth/github/callback",
    scope="read:user user:email",
)

GOOGLE_CONFIG = OAuth2Config(
    client_id="your-google-client-id",
    client_secret="your-google-client-secret",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
    redirect_uri="http://localhost:8000/auth/google/callback",
    scope="openid profile email",
)


# =============================================================================
# PKCE (Proof Key for Code Exchange)
# =============================================================================

class PKCEManager:
    """
    PKCE implementation for OAuth2.
    Used for public clients (mobile apps, SPAs) to prevent authorization code interception.
    """
    
    @staticmethod
    def generate_code_verifier(length: int = 64) -> str:
        """Generate a cryptographically random code verifier."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """Generate code challenge from verifier using SHA256."""
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    
    @staticmethod
    def generate_pkce_pair() -> tuple:
        """Generate PKCE code verifier and challenge pair."""
        verifier = PKCEManager.generate_code_verifier()
        challenge = PKCEManager.generate_code_challenge(verifier)
        return verifier, challenge


# =============================================================================
# OAuth2 State Management
# =============================================================================

class OAuth2StateStore:
    """
    Store for OAuth2 state parameters.
    In production, use Redis with TTL.
    """
    
    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {}
    
    def create_state(
        self,
        provider: str,
        redirect_to: Optional[str] = None,
        code_verifier: Optional[str] = None
    ) -> str:
        """Create and store OAuth2 state."""
        state = secrets.token_urlsafe(32)
        
        self._states[state] = {
            "provider": provider,
            "redirect_to": redirect_to,
            "code_verifier": code_verifier,
            "created_at": datetime.now(timezone.utc),
        }
        
        return state
    
    def validate_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Validate and consume state (one-time use)."""
        state_data = self._states.pop(state, None)
        
        if not state_data:
            return None
        
        # Check expiry (10 minutes)
        created = state_data["created_at"]
        if datetime.now(timezone.utc) - created > timedelta(minutes=10):
            return None
        
        return state_data


state_store = OAuth2StateStore()


# =============================================================================
# OAuth2 Client
# =============================================================================

class OAuth2Client:
    """
    OAuth2 client for handling authentication flows.
    """
    
    def __init__(self, config: OAuth2Config):
        self.config = config
    
    def get_authorization_url(
        self,
        state: str,
        code_challenge: Optional[str] = None
    ) -> str:
        """Get the authorization URL for the OAuth2 flow."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
            "state": state,
            "response_type": "code",
        }
        
        # Add PKCE parameters if provided
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        
        return f"{self.config.authorize_url}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        code_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
        }
        
        # Add code verifier for PKCE
        if code_verifier:
            data["code_verifier"] = code_verifier
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {response.text}",
                )
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information using access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info",
                )
            
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token refresh failed",
                )
            
            return response.json()


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(title="OAuth2 Authentication API")

github_client = OAuth2Client(GITHUB_CONFIG)
google_client = OAuth2Client(GOOGLE_CONFIG)


# =============================================================================
# GitHub OAuth2 Endpoints
# =============================================================================

@app.get("/auth/github/login")
async def github_login(redirect_to: Optional[str] = None):
    """
    Initiate GitHub OAuth2 login.
    """
    # Generate PKCE pair
    code_verifier, code_challenge = PKCEManager.generate_pkce_pair()
    
    # Create state with verifier
    state = state_store.create_state(
        provider="github",
        redirect_to=redirect_to,
        code_verifier=code_verifier,
    )
    
    # Get authorization URL
    auth_url = github_client.get_authorization_url(state, code_challenge)
    
    return RedirectResponse(url=auth_url)


@app.get("/auth/github/callback")
async def github_callback(code: str, state: str):
    """
    GitHub OAuth2 callback.
    """
    # Validate state
    state_data = state_store.validate_state(state)
    
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )
    
    # Exchange code for tokens
    tokens = await github_client.exchange_code(
        code=code,
        code_verifier=state_data.get("code_verifier"),
    )
    
    # Get user info
    user_info = await github_client.get_user_info(tokens["access_token"])
    
    # Here you would:
    # 1. Find or create user in your database
    # 2. Create session or JWT
    # 3. Redirect to frontend with token
    
    return {
        "message": "GitHub login successful",
        "tokens": tokens,
        "user": user_info,
        "redirect_to": state_data.get("redirect_to"),
    }


# =============================================================================
# Google OAuth2 Endpoints
# =============================================================================

@app.get("/auth/google/login")
async def google_login(redirect_to: Optional[str] = None):
    """
    Initiate Google OAuth2 login.
    """
    code_verifier, code_challenge = PKCEManager.generate_pkce_pair()
    
    state = state_store.create_state(
        provider="google",
        redirect_to=redirect_to,
        code_verifier=code_verifier,
    )
    
    auth_url = google_client.get_authorization_url(state, code_challenge)
    
    return RedirectResponse(url=auth_url)


@app.get("/auth/google/callback")
async def google_callback(code: str, state: str):
    """
    Google OAuth2 callback.
    """
    state_data = state_store.validate_state(state)
    
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )
    
    tokens = await google_client.exchange_code(
        code=code,
        code_verifier=state_data.get("code_verifier"),
    )
    
    user_info = await google_client.get_user_info(tokens["access_token"])
    
    return {
        "message": "Google login successful",
        "tokens": tokens,
        "user": user_info,
        "redirect_to": state_data.get("redirect_to"),
    }


# =============================================================================
# Client Credentials Flow (Service-to-Service)
# =============================================================================

class ClientCredentialsClient:
    """
    OAuth2 client credentials flow for service-to-service authentication.
    """
    
    def __init__(self, token_url: str, client_id: str, client_secret: str):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._token_cache: Optional[Dict] = None
        self._token_expires: Optional[datetime] = None
    
    async def get_token(self, scope: Optional[str] = None) -> str:
        """Get access token, using cache if valid."""
        # Check cache
        if self._token_cache and self._token_expires:
            if datetime.now(timezone.utc) < self._token_expires:
                return self._token_cache["access_token"]
        
        # Request new token
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        if scope:
            data["scope"] = scope
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get service token",
                )
            
            token_data = response.json()
            self._token_cache = token_data
            
            # Set expiry (with buffer)
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires = datetime.now(timezone.utc) + timedelta(
                seconds=expires_in - 60  # 60 second buffer
            )
            
            return token_data["access_token"]


# =============================================================================
# Demo Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "message": "OAuth2 Authentication API",
        "endpoints": {
            "github_login": "/auth/github/login",
            "google_login": "/auth/google/login",
        },
    }


@app.get("/pkce/demo")
async def pkce_demo():
    """Demonstrate PKCE generation."""
    verifier, challenge = PKCEManager.generate_pkce_pair()
    return {
        "code_verifier": verifier,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "note": "Verifier is kept secret, challenge is sent in auth request",
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    OAuth2 Authentication API
    ================================================
    
    Note: Replace OAuth2 configs with real credentials.
    
    Endpoints:
    - GET /auth/github/login - Start GitHub OAuth2 flow
    - GET /auth/google/login - Start Google OAuth2 flow
    - GET /pkce/demo - See PKCE generation
    
    OpenAPI docs: http://localhost:8000/docs
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
