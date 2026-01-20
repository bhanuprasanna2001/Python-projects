"""
CRUD Operations
===============
Create, Read, Update, Delete operations with SQLAlchemy.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from typing import Optional, List
from models import User, Post, Tag, Comment, Product


# ============================================================
# User CRUD
# ============================================================

class UserCRUD:
    """CRUD operations for User model."""
    
    @staticmethod
    def create(
        session: Session,
        username: str,
        email: str,
        password_hash: str,
        **kwargs
    ) -> User:
        """
        Create a new user.
        
        Args:
            session: Database session
            username: Unique username
            email: Unique email
            password_hash: Hashed password
            **kwargs: Additional user fields
            
        Returns:
            Created User object
        """
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            **kwargs
        )
        session.add(user)
        session.flush()  # Get ID without committing
        return user
    
    @staticmethod
    def get_by_id(session: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return session.get(User, user_id)
    
    @staticmethod
    def get_by_username(session: Session, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_email(session: Session, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[User]:
        """Get all users with pagination."""
        stmt = select(User)
        
        if active_only:
            stmt = stmt.where(User.is_active == True)
        
        stmt = stmt.offset(skip).limit(limit)
        result = session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def update(session: Session, user: User, **kwargs) -> User:
        """
        Update user fields.
        
        Args:
            session: Database session
            user: User object to update
            **kwargs: Fields to update
            
        Returns:
            Updated User object
        """
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        session.flush()
        return user
    
    @staticmethod
    def update_by_id(session: Session, user_id: int, **kwargs) -> bool:
        """
        Bulk update user by ID.
        More efficient for single field updates.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**kwargs)
        )
        result = session.execute(stmt)
        return result.rowcount > 0
    
    @staticmethod
    def delete(session: Session, user: User) -> None:
        """Delete user."""
        session.delete(user)
    
    @staticmethod
    def soft_delete(session: Session, user: User) -> User:
        """Soft delete (deactivate) user."""
        user.is_active = False
        session.flush()
        return user


# ============================================================
# Post CRUD
# ============================================================

class PostCRUD:
    """CRUD operations for Post model."""
    
    @staticmethod
    def create(
        session: Session,
        title: str,
        slug: str,
        author_id: int,
        content: str = "",
        tags: List[Tag] = None
    ) -> Post:
        """Create a new post."""
        post = Post(
            title=title,
            slug=slug,
            author_id=author_id,
            content=content
        )
        
        if tags:
            post.tags = tags
        
        session.add(post)
        session.flush()
        return post
    
    @staticmethod
    def get_by_id(session: Session, post_id: int) -> Optional[Post]:
        """Get post by ID."""
        return session.get(Post, post_id)
    
    @staticmethod
    def get_by_slug(session: Session, slug: str) -> Optional[Post]:
        """Get post by slug."""
        stmt = select(Post).where(Post.slug == slug)
        return session.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_published(
        session: Session,
        skip: int = 0,
        limit: int = 10
    ) -> List[Post]:
        """Get published posts."""
        stmt = (
            select(Post)
            .where(Post.is_published == True)
            .order_by(Post.published_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())
    
    @staticmethod
    def get_by_author(
        session: Session,
        author_id: int,
        include_drafts: bool = False
    ) -> List[Post]:
        """Get all posts by an author."""
        stmt = select(Post).where(Post.author_id == author_id)
        
        if not include_drafts:
            stmt = stmt.where(Post.is_published == True)
        
        stmt = stmt.order_by(Post.created_at.desc())
        return list(session.execute(stmt).scalars().all())
    
    @staticmethod
    def increment_views(session: Session, post_id: int) -> None:
        """Increment post view count atomically."""
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(view_count=Post.view_count + 1)
        )
        session.execute(stmt)
    
    @staticmethod
    def add_tag(session: Session, post: Post, tag: Tag) -> Post:
        """Add a tag to a post."""
        if tag not in post.tags:
            post.tags.append(tag)
            session.flush()
        return post
    
    @staticmethod
    def remove_tag(session: Session, post: Post, tag: Tag) -> Post:
        """Remove a tag from a post."""
        if tag in post.tags:
            post.tags.remove(tag)
            session.flush()
        return post


# ============================================================
# Product CRUD (for query examples)
# ============================================================

class ProductCRUD:
    """CRUD operations for Product model."""
    
    @staticmethod
    def create(session: Session, **kwargs) -> Product:
        """Create a new product."""
        product = Product(**kwargs)
        session.add(product)
        session.flush()
        return product
    
    @staticmethod
    def bulk_create(session: Session, products: List[dict]) -> List[Product]:
        """
        Bulk create products efficiently.
        
        Args:
            session: Database session
            products: List of product dictionaries
            
        Returns:
            List of created Product objects
        """
        product_objects = [Product(**p) for p in products]
        session.add_all(product_objects)
        session.flush()
        return product_objects
    
    @staticmethod
    def get_by_category(
        session: Session,
        category: str,
        in_stock_only: bool = False
    ) -> List[Product]:
        """Get products by category."""
        stmt = select(Product).where(Product.category == category)
        
        if in_stock_only:
            stmt = stmt.where(Product.stock > 0)
        
        return list(session.execute(stmt).scalars().all())
    
    @staticmethod
    def update_stock(session: Session, product_id: int, quantity: int) -> bool:
        """
        Update product stock (add/subtract).
        
        Args:
            product_id: Product ID
            quantity: Amount to add (positive) or subtract (negative)
        """
        stmt = (
            update(Product)
            .where(Product.id == product_id)
            .where(Product.stock + quantity >= 0)  # Prevent negative stock
            .values(stock=Product.stock + quantity)
        )
        result = session.execute(stmt)
        return result.rowcount > 0
    
    @staticmethod
    def bulk_update_prices(
        session: Session,
        category: str,
        percentage: float
    ) -> int:
        """
        Bulk update prices for a category.
        
        Args:
            category: Product category
            percentage: Price adjustment (e.g., 0.1 for 10% increase)
            
        Returns:
            Number of updated products
        """
        stmt = (
            update(Product)
            .where(Product.category == category)
            .values(price=Product.price * (1 + percentage))
        )
        result = session.execute(stmt)
        return result.rowcount
    
    @staticmethod
    def delete_inactive(session: Session) -> int:
        """Delete all inactive products."""
        stmt = delete(Product).where(Product.is_active == False)
        result = session.execute(stmt)
        return result.rowcount
