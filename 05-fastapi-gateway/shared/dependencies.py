"""
Shared Dependencies
===================
Reusable FastAPI dependencies.
"""

from fastapi import Header, HTTPException, Depends, Query
from typing import Optional
import time


# ============================================================
# Authentication Dependencies
# ============================================================

async def get_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Validate API key from header.
    
    Usage:
        @app.get("/protected")
        async def protected(api_key: str = Depends(get_api_key)):
            ...
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # In production, validate against database
    valid_keys = ["demo-key-123", "test-key-456"]
    
    if x_api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return x_api_key


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Extract and validate current user from token.
    
    Usage:
        @app.get("/me")
        async def get_me(user: dict = Depends(get_current_user)):
            return user
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    # In production, decode JWT token
    # For demo, return mock user
    return {
        "id": 1,
        "username": "demo_user",
        "email": "demo@example.com",
        "roles": ["user"]
    }


def require_roles(*required_roles: str):
    """
    Role-based access control dependency.
    
    Usage:
        @app.get("/admin")
        async def admin_only(user: dict = Depends(require_roles("admin"))):
            ...
    """
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_roles = set(user.get("roles", []))
        
        if not user_roles.intersection(required_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Required roles: {required_roles}"
            )
        
        return user
    
    return role_checker


# ============================================================
# Pagination Dependencies
# ============================================================

async def pagination_params(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=10, ge=1, le=100, description="Items per page")
) -> dict:
    """
    Common pagination parameters.
    
    Usage:
        @app.get("/items")
        async def list_items(pagination: dict = Depends(pagination_params)):
            skip = (pagination["page"] - 1) * pagination["per_page"]
            ...
    """
    return {
        "page": page,
        "per_page": per_page,
        "skip": (page - 1) * per_page
    }


# ============================================================
# Rate Limiting Dependencies
# ============================================================

# Simple in-memory rate limiter (use Redis in production)
request_counts: dict = {}


async def rate_limiter(
    x_api_key: str = Depends(get_api_key),
    limit: int = 100,
    window: int = 60
) -> None:
    """
    Simple rate limiter.
    
    Args:
        limit: Max requests per window
        window: Time window in seconds
    """
    current_time = int(time.time())
    window_start = current_time - (current_time % window)
    key = f"{x_api_key}:{window_start}"
    
    count = request_counts.get(key, 0)
    
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(window)}
        )
    
    request_counts[key] = count + 1
    
    # Cleanup old entries
    for k in list(request_counts.keys()):
        if k.split(":")[1] != str(window_start):
            del request_counts[k]


# ============================================================
# Database Dependencies
# ============================================================

class DatabaseSession:
    """Mock database session for demo."""
    
    def __init__(self):
        self.connected = True
    
    def query(self, model):
        return self
    
    def close(self):
        self.connected = False


async def get_db():
    """
    Database session dependency.
    
    Usage:
        @app.get("/users")
        async def get_users(db: DatabaseSession = Depends(get_db)):
            ...
    """
    db = DatabaseSession()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# Request Context Dependencies
# ============================================================

async def get_request_id(
    x_request_id: Optional[str] = Header(None)
) -> str:
    """
    Get or generate request ID for tracing.
    """
    if x_request_id:
        return x_request_id
    
    import uuid
    return str(uuid.uuid4())
