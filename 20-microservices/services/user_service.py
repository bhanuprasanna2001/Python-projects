"""
User Microservice
=================
Handles user-related operations.
"""

from fastapi import FastAPI, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timezone
import uuid


# =============================================================================
# Models
# =============================================================================

class UserCreate(BaseModel):
    name: str
    email: str
    role: str = "customer"


class User(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


# =============================================================================
# In-Memory Database
# =============================================================================

class UserDatabase:
    """Simple in-memory user storage."""
    
    def __init__(self):
        self._users: Dict[int, Dict] = {}
        self._counter = 0
        
        # Add sample users
        self._add_sample_users()
    
    def _add_sample_users(self):
        samples = [
            {"name": "John Doe", "email": "john@example.com", "role": "admin"},
            {"name": "Jane Smith", "email": "jane@example.com", "role": "customer"},
            {"name": "Bob Wilson", "email": "bob@example.com", "role": "customer"},
        ]
        for user in samples:
            self.create(user)
    
    def create(self, data: Dict) -> Dict:
        self._counter += 1
        user = {
            "id": self._counter,
            "name": data["name"],
            "email": data["email"],
            "role": data.get("role", "customer"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._users[self._counter] = user
        return user
    
    def get(self, user_id: int) -> Optional[Dict]:
        return self._users.get(user_id)
    
    def get_all(self) -> List[Dict]:
        return list(self._users.values())
    
    def get_by_email(self, email: str) -> Optional[Dict]:
        for user in self._users.values():
            if user["email"] == email:
                return user
        return None
    
    def update(self, user_id: int, data: Dict) -> Optional[Dict]:
        if user_id not in self._users:
            return None
        
        user = self._users[user_id]
        for key, value in data.items():
            if value is not None:
                user[key] = value
        
        return user
    
    def delete(self, user_id: int) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False


db = UserDatabase()


# =============================================================================
# App
# =============================================================================

app = FastAPI(
    title="User Service",
    description="User management microservice",
    version="1.0.0",
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "service": "User Service",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "user"}


@app.get("/users", response_model=List[Dict])
async def list_users(
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """List all users."""
    print(f"[{x_correlation_id}] Listing all users")
    return db.get_all()


@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Get user by ID."""
    print(f"[{x_correlation_id}] Getting user {user_id}")
    
    user = db.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user


@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Create a new user."""
    print(f"[{x_correlation_id}] Creating user: {data.email}")
    
    # Check if email already exists
    if db.get_by_email(data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    user = db.create(data.model_dump())
    return user


@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Update user."""
    print(f"[{x_correlation_id}] Updating user {user_id}")
    
    user = db.update(user_id, data.model_dump(exclude_none=True))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Delete user."""
    print(f"[{x_correlation_id}] Deleting user {user_id}")
    
    if not db.delete(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )


# =============================================================================
# Internal Endpoints (for service-to-service communication)
# =============================================================================

@app.get("/internal/users/{user_id}/exists")
async def check_user_exists(user_id: int):
    """
    Internal endpoint for other services to check if user exists.
    """
    return {"exists": db.get(user_id) is not None}


@app.post("/internal/users/validate-batch")
async def validate_users_batch(user_ids: List[int]):
    """
    Validate multiple users at once.
    """
    results = {}
    for user_id in user_ids:
        user = db.get(user_id)
        results[user_id] = {
            "exists": user is not None,
            "name": user["name"] if user else None,
        }
    return results


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    User Service
    ================================================
    
    Endpoints:
    - GET /users - List all users
    - GET /users/{id} - Get user by ID
    - POST /users - Create user
    - PUT /users/{id} - Update user
    - DELETE /users/{id} - Delete user
    
    Internal endpoints:
    - GET /internal/users/{id}/exists
    - POST /internal/users/validate-batch
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
