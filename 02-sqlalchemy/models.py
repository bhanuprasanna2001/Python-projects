"""
SQLAlchemy Models
=================
Demonstrates model definitions with various relationships.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, Table, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from datetime import datetime
from database import Base


# ============================================================
# Association Table for Many-to-Many
# ============================================================

# Post <-> Tag (Many-to-Many)
post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

# User <-> Role (Many-to-Many with extra data)
class UserRole(Base):
    """Association table with additional attributes."""
    __tablename__ = 'user_roles'
    
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


# ============================================================
# User Model
# ============================================================

class User(Base):
    """
    User model demonstrating:
    - Basic columns with constraints
    - One-to-Many relationship (User -> Posts)
    - Many-to-Many through association (User <-> Roles)
    - Self-referential relationship (followers)
    """
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic fields with constraints
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Profile fields
    full_name = Column(String(100))
    bio = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # ---- Relationships ----
    
    # One-to-Many: User -> Posts
    posts = relationship(
        "Post",
        back_populates="author",
        lazy="dynamic",  # Returns query, not list (good for large sets)
        cascade="all, delete-orphan"  # Delete posts when user deleted
    )
    
    # One-to-Many: User -> Comments
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    
    # Many-to-Many: User <-> Roles (through association)
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        viewonly=True  # Read-only, use user_roles for writes
    )
    
    # One-to-One: User -> Profile
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    # Table-level constraints
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        CheckConstraint('length(username) >= 3', name='username_min_length'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


# ============================================================
# Profile Model (One-to-One with User)
# ============================================================

class Profile(Base):
    """User profile - One-to-One relationship."""
    __tablename__ = 'profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    
    avatar_url = Column(String(500))
    website = Column(String(200))
    location = Column(String(100))
    birth_date = Column(DateTime)
    
    # Back reference
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<Profile(user_id={self.user_id})>"


# ============================================================
# Post Model (One-to-Many with User, Many-to-Many with Tag)
# ============================================================

class Post(Base):
    """Blog post model."""
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    content = Column(Text)
    
    # Status
    is_published = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    
    # Foreign key to User
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)
    
    # ---- Relationships ----
    
    # Many-to-One: Post -> User
    author = relationship("User", back_populates="posts")
    
    # One-to-Many: Post -> Comments
    comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="Comment.created_at"  # Order by creation date
    )
    
    # Many-to-Many: Post <-> Tags
    tags = relationship(
        "Tag",
        secondary=post_tags,
        back_populates="posts",
        lazy="selectin"  # Eager load with separate SELECT
    )
    
    __table_args__ = (
        Index('idx_post_author_published', 'author_id', 'is_published'),
    )
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title[:30]}...')>"


# ============================================================
# Comment Model (Self-referential for replies)
# ============================================================

class Comment(Base):
    """Comment with nested replies (self-referential)."""
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    
    # Foreign keys
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    
    # Self-reference for replies
    parent_id = Column(Integer, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ---- Relationships ----
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    
    # Self-referential relationship
    replies = relationship(
        "Comment",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Comment(id={self.id}, author_id={self.author_id})>"


# ============================================================
# Tag Model (Many-to-Many with Post)
# ============================================================

class Tag(Base):
    """Tag for categorizing posts."""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    
    # Many-to-Many with Posts
    posts = relationship("Post", secondary=post_tags, back_populates="tags")
    
    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"


# ============================================================
# Role Model (Many-to-Many with User)
# ============================================================

class Role(Base):
    """User role for permissions."""
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    permissions = Column(Text)  # JSON string of permissions
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role")
    users = relationship("User", secondary="user_roles", back_populates="roles", viewonly=True)
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


# ============================================================
# Product Model (for query examples)
# ============================================================

class Product(Base):
    """Product model for query demonstrations."""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Computed column example (at application level)
    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0
    
    __table_args__ = (
        CheckConstraint('price >= 0', name='price_positive'),
        CheckConstraint('stock >= 0', name='stock_positive'),
    )
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"
