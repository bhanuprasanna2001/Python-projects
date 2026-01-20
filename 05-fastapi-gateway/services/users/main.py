"""
Users Microservice
==================
Handles user-related operations.
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import sys
sys.path.insert(0, '..')

from shared.models import UserCreate, UserUpdate, UserResponse
from shared.dependencies import pagination_params

app = FastAPI(title="Users Service", version="1.0.0")

# In-memory database for demo
users_db: dict = {
    1: {
        "id": 1,
        "email": "john@example.com",
        "username": "john",
        "full_name": "John Doe",
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    2: {
        "id": 2,
        "email": "jane@example.com",
        "username": "jane",
        "full_name": "Jane Smith",
        "is_active": True,
        "created_at": datetime.utcnow()
    }
}
next_id = 3


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "users"}


@app.get("/stats")
async def stats():
    return {
        "total_users": len(users_db),
        "active_users": sum(1 for u in users_db.values() if u["is_active"])
    }


@app.get("/", response_model=List[UserResponse])
async def list_users(
    pagination: dict = Depends(pagination_params),
    is_active: Optional[bool] = Query(None)
):
    """List all users with pagination."""
    users = list(users_db.values())
    
    if is_active is not None:
        users = [u for u in users if u["is_active"] == is_active]
    
    start = pagination["skip"]
    end = start + pagination["per_page"]
    
    return users[start:end]


@app.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Get user by ID."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]


@app.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """Create a new user."""
    global next_id
    
    # Check for existing email/username
    for u in users_db.values():
        if u["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        if u["username"] == user.username:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    new_user = {
        "id": next_id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    users_db[next_id] = new_user
    next_id += 1
    
    return new_user


@app.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate):
    """Update user fields."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[user_id]
    update_data = user_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        user[key] = value
    
    return user


@app.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int):
    """Delete a user."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    del users_db[user_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
