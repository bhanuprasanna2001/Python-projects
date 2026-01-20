"""
FastAPI JWT Authentication
==========================
Complete JWT authentication integration with FastAPI.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone
import jwt
from token_service import TokenService, TokenConfig, ExtendedTokenService


# =============================================================================
# Models
# =============================================================================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str
    role: str
    permissions: List[str]
    exp: datetime


# =============================================================================
# Fake User Database (use real DB in production)
# =============================================================================

fake_users_db = {
    "user1": {
        "id": "user1",
        "username": "john_doe",
        "email": "john@example.com",
        "hashed_password": "hashed_secret123",  # Use proper hashing!
        "role": "user",
        "permissions": ["read"],
        "is_active": True,
    },
    "admin1": {
        "id": "admin1",
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "hashed_admin123",
        "role": "admin",
        "permissions": ["read", "write", "delete", "admin"],
        "is_active": True,
    },
}

# Username to ID mapping
username_to_id = {user["username"]: user_id for user_id, user in fake_users_db.items()}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Fake password verification (use passlib in production)."""
    return f"hashed_{plain_password}" == hashed_password


def get_user(user_id: str) -> Optional[dict]:
    """Get user from database."""
    return fake_users_db.get(user_id)


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username."""
    user_id = username_to_id.get(username)
    if user_id:
        return fake_users_db.get(user_id)
    return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="JWT Authentication API",
    description="FastAPI with JWT authentication",
    version="1.0.0",
)

# Token service
token_config = TokenConfig(
    secret_key="your-super-secret-key-change-in-production",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7,
)
token_service = ExtendedTokenService(token_config)


# =============================================================================
# Security Schemes
# =============================================================================

# Option 1: HTTPBearer (for Authorization: Bearer <token>)
http_bearer = HTTPBearer()

# Option 2: OAuth2 (for OpenAPI/Swagger integration)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# =============================================================================
# Dependencies
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> dict:
    """
    Dependency to extract and validate current user from JWT.
    """
    token = credentials.credentials
    
    try:
        payload = token_service.verify_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = get_user(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )
    
    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Dependency for active users only."""
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


def require_role(required_role: str):
    """Dependency factory for role-based access control."""
    async def role_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return current_user
    return role_checker


def require_permission(required_permission: str):
    """Dependency factory for permission-based access control."""
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        permissions = current_user.get("permissions", [])
        if required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )
        return current_user
    return permission_checker


def require_any_permission(required_permissions: List[str]):
    """Dependency factory requiring any of the listed permissions."""
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        user_permissions = set(current_user.get("permissions", []))
        required = set(required_permissions)
        
        if not user_permissions.intersection(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of permissions {required_permissions} required",
            )
        return current_user
    return permission_checker


# =============================================================================
# Endpoints
# =============================================================================

@app.post("/auth/login", response_model=TokenResponse)
async def login(form_data: UserLogin):
    """
    Login endpoint - authenticate and return tokens.
    """
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, refresh_token = token_service.create_token_pair(
        user_id=user["id"],
        extra_claims={
            "role": user["role"],
            "permissions": user["permissions"],
        },
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=token_config.access_token_expire_minutes * 60,
    )


@app.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2-compatible token endpoint for Swagger UI.
    """
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, refresh_token = token_service.create_token_pair(
        user_id=user["id"],
        extra_claims={
            "role": user["role"],
            "permissions": user["permissions"],
        },
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=token_config.access_token_expire_minutes * 60,
    )


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = token_service.verify_refresh_token(request.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    
    user_id = payload.get("sub")
    user = get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Create new token pair
    access_token, new_refresh_token = token_service.create_token_pair(
        user_id=user["id"],
        extra_claims={
            "role": user["role"],
            "permissions": user["permissions"],
        },
    )
    
    # Optionally revoke old refresh token (rotation)
    token_service.revoke_token(request.refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=token_config.access_token_expire_minutes * 60,
    )


@app.post("/auth/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
):
    """
    Logout - revoke current access token.
    """
    token_service.revoke_token(credentials.credentials)
    return {"message": "Successfully logged out"}


@app.get("/users/me", response_model=UserResponse)
async def read_users_me(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user profile.
    """
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        is_active=current_user["is_active"],
    )


@app.get("/users/me/permissions")
async def read_user_permissions(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user's permissions.
    """
    return {
        "user_id": current_user["id"],
        "role": current_user["role"],
        "permissions": current_user["permissions"],
    }


# =============================================================================
# Protected Endpoints (Role/Permission-based)
# =============================================================================

@app.get("/admin/dashboard")
async def admin_dashboard(
    current_user: dict = Depends(require_role("admin"))
):
    """
    Admin-only endpoint.
    """
    return {
        "message": "Welcome to admin dashboard",
        "user": current_user["username"],
    }


@app.get("/protected/write")
async def protected_write(
    current_user: dict = Depends(require_permission("write"))
):
    """
    Requires 'write' permission.
    """
    return {
        "message": "You have write access",
        "user": current_user["username"],
    }


@app.get("/protected/delete")
async def protected_delete(
    current_user: dict = Depends(require_permission("delete"))
):
    """
    Requires 'delete' permission.
    """
    return {
        "message": "You have delete access",
        "user": current_user["username"],
    }


@app.get("/protected/read-or-write")
async def protected_read_or_write(
    current_user: dict = Depends(require_any_permission(["read", "write"]))
):
    """
    Requires either 'read' or 'write' permission.
    """
    return {
        "message": "You have read or write access",
        "user": current_user["username"],
        "permissions": current_user["permissions"],
    }


# =============================================================================
# Public Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Public endpoint."""
    return {"message": "Welcome to JWT Auth API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    JWT Authentication API
    ================================================
    
    Test credentials:
    - Username: john_doe, Password: secret123 (role: user)
    - Username: admin, Password: admin123 (role: admin)
    
    Endpoints:
    - POST /auth/login - Login and get tokens
    - POST /auth/refresh - Refresh access token
    - POST /auth/logout - Revoke token
    - GET /users/me - Get current user (requires auth)
    - GET /admin/dashboard - Admin only
    - GET /protected/write - Requires 'write' permission
    
    OpenAPI docs: http://localhost:8000/docs
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
