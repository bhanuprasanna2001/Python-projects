"""
Session-Based Authentication
============================
Session management with FastAPI using cookies.
"""

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
import secrets
import hashlib
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class SessionConfig:
    secret_key: str = "your-secret-key-change-in-production"
    session_cookie_name: str = "session_id"
    max_age: int = 3600  # 1 hour
    secure: bool = False  # Set True in production (HTTPS only)
    httponly: bool = True
    samesite: str = "lax"  # "strict", "lax", or "none"


config = SessionConfig()


# =============================================================================
# Session Store (In-memory - use Redis in production)
# =============================================================================

class SessionStore:
    """
    In-memory session store.
    In production, use Redis or database.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create(self, user_id: str, data: Optional[Dict] = None) -> str:
        """Create a new session and return session ID."""
        session_id = secrets.token_urlsafe(32)
        
        self._sessions[session_id] = {
            "user_id": user_id,
            "data": data or {},
            "created_at": datetime.now(timezone.utc),
            "last_accessed": datetime.now(timezone.utc),
        }
        
        return session_id
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        session = self._sessions.get(session_id)
        
        if session:
            # Check expiry
            if self._is_expired(session):
                self.delete(session_id)
                return None
            
            # Update last accessed
            session["last_accessed"] = datetime.now(timezone.utc)
        
        return session
    
    def update(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data."""
        session = self._sessions.get(session_id)
        if session:
            session["data"].update(data)
            session["last_accessed"] = datetime.now(timezone.utc)
            return True
        return False
    
    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user."""
        to_delete = [
            sid for sid, session in self._sessions.items()
            if session["user_id"] == user_id
        ]
        for sid in to_delete:
            del self._sessions[sid]
        return len(to_delete)
    
    def _is_expired(self, session: Dict) -> bool:
        """Check if session is expired."""
        last_accessed = session["last_accessed"]
        expiry = last_accessed + timedelta(seconds=config.max_age)
        return datetime.now(timezone.utc) > expiry
    
    def cleanup_expired(self) -> int:
        """Remove all expired sessions."""
        expired = [
            sid for sid, session in self._sessions.items()
            if self._is_expired(session)
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


# Global session store
session_store = SessionStore()


# =============================================================================
# Signed Session (Alternative using itsdangerous)
# =============================================================================

class SignedSessionManager:
    """
    Session manager using signed cookies.
    Session data is stored in the cookie itself (client-side).
    Good for small session data, no server-side storage needed.
    """
    
    def __init__(self, secret_key: str, max_age: int = 3600):
        self.serializer = URLSafeTimedSerializer(secret_key)
        self.max_age = max_age
    
    def create_session(self, data: Dict[str, Any]) -> str:
        """Create a signed session token."""
        return self.serializer.dumps(data)
    
    def load_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Load and verify a session token."""
        try:
            data = self.serializer.loads(token, max_age=self.max_age)
            return data
        except SignatureExpired:
            return None  # Session expired
        except BadSignature:
            return None  # Invalid signature
    
    def refresh_session(self, token: str) -> Optional[str]:
        """Refresh session (create new token with same data)."""
        data = self.load_session(token)
        if data:
            return self.create_session(data)
        return None


signed_session_manager = SignedSessionManager(config.secret_key)


# =============================================================================
# Fake User Database
# =============================================================================

fake_users_db = {
    "user1": {
        "id": "user1",
        "username": "john",
        "email": "john@example.com",
        "hashed_password": "hashed_password123",
        "is_active": True,
    },
    "user2": {
        "id": "user2",
        "username": "jane",
        "email": "jane@example.com",
        "hashed_password": "hashed_password456",
        "is_active": True,
    },
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user (fake implementation)."""
    for user in fake_users_db.values():
        if user["username"] == username:
            if f"hashed_{password}" == user["hashed_password"]:
                return user
    return None


# =============================================================================
# Models
# =============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(title="Session Authentication API")


# =============================================================================
# Dependencies
# =============================================================================

async def get_session(request: Request) -> Optional[Dict[str, Any]]:
    """Get current session from cookie."""
    session_id = request.cookies.get(config.session_cookie_name)
    
    if not session_id:
        return None
    
    return session_store.get(session_id)


async def require_session(
    session: Optional[Dict] = Depends(get_session)
) -> Dict[str, Any]:
    """Require valid session."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return session


async def get_current_user(
    session: Dict = Depends(require_session)
) -> dict:
    """Get current user from session."""
    user_id = session.get("user_id")
    user = fake_users_db.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


# =============================================================================
# CSRF Protection
# =============================================================================

def generate_csrf_token(session_id: str) -> str:
    """Generate CSRF token tied to session."""
    return hashlib.sha256(f"{session_id}{config.secret_key}".encode()).hexdigest()


def verify_csrf_token(session_id: str, token: str) -> bool:
    """Verify CSRF token."""
    expected = generate_csrf_token(session_id)
    return secrets.compare_digest(expected, token)


# =============================================================================
# Endpoints
# =============================================================================

@app.post("/auth/login")
async def login(request: LoginRequest, response: Response):
    """
    Login and create session.
    """
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Create session
    session_id = session_store.create(
        user_id=user["id"],
        data={"login_time": datetime.now(timezone.utc).isoformat()}
    )
    
    # Set session cookie
    response.set_cookie(
        key=config.session_cookie_name,
        value=session_id,
        max_age=config.max_age,
        httponly=config.httponly,
        secure=config.secure,
        samesite=config.samesite,
    )
    
    # Generate CSRF token
    csrf_token = generate_csrf_token(session_id)
    
    return {
        "message": "Login successful",
        "user": UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
        ),
        "csrf_token": csrf_token,  # Send to client, store in JS
    }


@app.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    session: Dict = Depends(require_session)
):
    """
    Logout and destroy session.
    """
    session_id = request.cookies.get(config.session_cookie_name)
    
    if session_id:
        session_store.delete(session_id)
    
    # Clear cookie
    response.delete_cookie(
        key=config.session_cookie_name,
        httponly=config.httponly,
        secure=config.secure,
        samesite=config.samesite,
    )
    
    return {"message": "Logout successful"}


@app.post("/auth/logout-all")
async def logout_all_sessions(
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """
    Logout from all sessions (all devices).
    """
    deleted = session_store.delete_user_sessions(current_user["id"])
    
    response.delete_cookie(
        key=config.session_cookie_name,
        httponly=config.httponly,
        secure=config.secure,
        samesite=config.samesite,
    )
    
    return {"message": f"Logged out from {deleted} session(s)"}


@app.get("/users/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile.
    """
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
    )


@app.get("/session/info")
async def session_info(
    request: Request,
    session: Dict = Depends(require_session)
):
    """
    Get session information.
    """
    return {
        "user_id": session["user_id"],
        "created_at": session["created_at"].isoformat(),
        "last_accessed": session["last_accessed"].isoformat(),
        "data": session["data"],
    }


@app.put("/session/data")
async def update_session_data(
    request: Request,
    data: Dict[str, Any],
    session: Dict = Depends(require_session)
):
    """
    Update custom session data.
    """
    session_id = request.cookies.get(config.session_cookie_name)
    session_store.update(session_id, data)
    return {"message": "Session data updated"}


# =============================================================================
# Signed Session Endpoints (Alternative)
# =============================================================================

@app.post("/auth/signed/login")
async def signed_login(request: LoginRequest, response: Response):
    """
    Login using signed session (client-side storage).
    """
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Create signed session token
    session_token = signed_session_manager.create_session({
        "user_id": user["id"],
        "username": user["username"],
        "login_time": datetime.now(timezone.utc).isoformat(),
    })
    
    response.set_cookie(
        key="signed_session",
        value=session_token,
        max_age=config.max_age,
        httponly=config.httponly,
        secure=config.secure,
        samesite=config.samesite,
    )
    
    return {"message": "Login successful"}


@app.get("/auth/signed/me")
async def signed_me(request: Request):
    """
    Get current user from signed session.
    """
    session_token = request.cookies.get("signed_session")
    
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    session_data = signed_session_manager.load_session(session_token)
    
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )
    
    return session_data


# =============================================================================
# Health Check
# =============================================================================

@app.get("/")
async def root():
    return {"message": "Session Authentication API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    Session Authentication API
    ================================================
    
    Test credentials:
    - Username: john, Password: password123
    - Username: jane, Password: password456
    
    Endpoints:
    - POST /auth/login - Login and create session
    - POST /auth/logout - Logout and destroy session
    - GET /users/me - Get current user (requires session)
    - GET /session/info - Get session details
    
    OpenAPI docs: http://localhost:8000/docs
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
