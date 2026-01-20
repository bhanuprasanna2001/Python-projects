"""
Shared Pydantic Models
======================
Models shared across services.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================================
# Base Models
# ============================================================

class BaseResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: str = "OK"
    data: Optional[dict] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List
    total: int
    page: int
    per_page: int
    pages: int


# ============================================================
# User Models
# ============================================================

class UserBase(BaseModel):
    """Base user fields."""
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation request."""
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    """User update request (all fields optional)."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response (no password)."""
    id: int
    is_active: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# Product Models
# ============================================================

class ProductCategory(str, Enum):
    """Product categories."""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    FOOD = "food"
    OTHER = "other"


class ProductBase(BaseModel):
    """Base product fields."""
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    price: float = Field(gt=0)
    category: ProductCategory = ProductCategory.OTHER


class ProductCreate(ProductBase):
    """Product creation request."""
    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    """Product update request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    category: Optional[ProductCategory] = None
    stock: Optional[int] = Field(default=None, ge=0)


class ProductResponse(ProductBase):
    """Product response."""
    id: int
    stock: int
    is_active: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# Error Models
# ============================================================

class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
