"""
Advanced Queries
================
Demonstrates complex SQLAlchemy query patterns.
"""

from sqlalchemy import select, func, case, and_, or_, desc, asc, text, literal
from sqlalchemy.orm import Session, joinedload, selectinload, contains_eager
from typing import List, Dict, Any, Tuple
from models import User, Post, Tag, Comment, Product, post_tags


class QueryExamples:
    """Collection of advanced query examples."""
    
    # ============================================================
    # Basic Filtering
    # ============================================================
    
    @staticmethod
    def filter_examples(session: Session):
        """Various filtering techniques."""
        
        # Equality
        stmt = select(User).where(User.username == "john")
        
        # Not equal
        stmt = select(User).where(User.username != "john")
        
        # IN clause
        stmt = select(User).where(User.id.in_([1, 2, 3]))
        
        # NOT IN
        stmt = select(User).where(~User.id.in_([1, 2, 3]))
        
        # LIKE (case-sensitive)
        stmt = select(User).where(User.username.like("john%"))
        
        # ILIKE (case-insensitive, PostgreSQL)
        stmt = select(User).where(User.username.ilike("%john%"))
        
        # BETWEEN
        stmt = select(Product).where(Product.price.between(10, 100))
        
        # IS NULL
        stmt = select(User).where(User.last_login.is_(None))
        
        # IS NOT NULL
        stmt = select(User).where(User.last_login.isnot(None))
        
        # AND conditions
        stmt = select(User).where(
            and_(
                User.is_active == True,
                User.email.like("%@gmail.com")
            )
        )
        
        # OR conditions
        stmt = select(User).where(
            or_(
                User.username == "admin",
                User.email.like("%@admin.com")
            )
        )
        
        # Complex nested conditions
        stmt = select(Product).where(
            or_(
                and_(Product.category == "electronics", Product.price > 100),
                and_(Product.category == "books", Product.stock > 50)
            )
        )
        
        return session.execute(stmt).scalars().all()
    
    # ============================================================
    # Ordering and Limiting
    # ============================================================
    
    @staticmethod
    def ordering_examples(session: Session):
        """Sorting and pagination."""
        
        # Simple ordering
        stmt = select(Product).order_by(Product.price)
        
        # Descending order
        stmt = select(Product).order_by(desc(Product.price))
        
        # Multiple columns
        stmt = select(Product).order_by(
            Product.category,
            desc(Product.price)
        )
        
        # NULLS FIRST / LAST (PostgreSQL)
        stmt = select(User).order_by(User.last_login.desc().nulls_last())
        
        # Pagination
        page = 1
        per_page = 10
        stmt = (
            select(Product)
            .order_by(Product.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        
        return session.execute(stmt).scalars().all()
    
    # ============================================================
    # Aggregations
    # ============================================================
    
    @staticmethod
    def aggregation_examples(session: Session) -> Dict[str, Any]:
        """Aggregate functions."""
        
        # Count all
        count_stmt = select(func.count()).select_from(Product)
        total = session.execute(count_stmt).scalar()
        
        # Count with condition
        active_count = session.execute(
            select(func.count()).where(Product.is_active == True)
        ).scalar()
        
        # Sum
        total_stock = session.execute(
            select(func.sum(Product.stock))
        ).scalar()
        
        # Average
        avg_price = session.execute(
            select(func.avg(Product.price))
        ).scalar()
        
        # Min/Max
        min_price = session.execute(
            select(func.min(Product.price))
        ).scalar()
        
        max_price = session.execute(
            select(func.max(Product.price))
        ).scalar()
        
        # Multiple aggregations
        stats = session.execute(
            select(
                func.count().label("count"),
                func.sum(Product.stock).label("total_stock"),
                func.avg(Product.price).label("avg_price"),
                func.min(Product.price).label("min_price"),
                func.max(Product.price).label("max_price")
            )
        ).one()
        
        return {
            "total": total,
            "active_count": active_count,
            "total_stock": total_stock,
            "avg_price": float(avg_price) if avg_price else 0,
            "min_price": min_price,
            "max_price": max_price
        }
    
    # ============================================================
    # Group By
    # ============================================================
    
    @staticmethod
    def group_by_examples(session: Session) -> List[Tuple]:
        """Grouping and having clauses."""
        
        # Products per category
        stmt = (
            select(
                Product.category,
                func.count().label("product_count"),
                func.avg(Product.price).label("avg_price")
            )
            .group_by(Product.category)
        )
        
        results = session.execute(stmt).all()
        
        # With HAVING clause
        stmt = (
            select(
                Product.category,
                func.count().label("count")
            )
            .group_by(Product.category)
            .having(func.count() > 5)
        )
        
        # Posts per user with user info
        stmt = (
            select(
                User.username,
                func.count(Post.id).label("post_count")
            )
            .join(Post, User.id == Post.author_id)
            .group_by(User.id, User.username)
            .having(func.count(Post.id) > 0)
            .order_by(desc("post_count"))
        )
        
        return session.execute(stmt).all()
    
    # ============================================================
    # Joins
    # ============================================================
    
    @staticmethod
    def join_examples(session: Session):
        """Various join operations."""
        
        # Inner join
        stmt = (
            select(Post, User)
            .join(User, Post.author_id == User.id)
        )
        
        # Left outer join
        stmt = (
            select(User, Post)
            .outerjoin(Post, User.id == Post.author_id)
        )
        
        # Multiple joins
        stmt = (
            select(Comment)
            .join(User, Comment.author_id == User.id)
            .join(Post, Comment.post_id == Post.id)
            .where(Post.is_published == True)
        )
        
        # Join with relationship (simpler syntax)
        stmt = (
            select(Post)
            .join(Post.author)
            .where(User.is_active == True)
        )
        
        # Many-to-many join
        stmt = (
            select(Post, Tag)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .join(Tag, post_tags.c.tag_id == Tag.id)
            .where(Tag.name == "python")
        )
        
        return session.execute(stmt).all()
    
    # ============================================================
    # Eager Loading (N+1 Prevention)
    # ============================================================
    
    @staticmethod
    def eager_loading_examples(session: Session):
        """
        Eager loading to prevent N+1 query problem.
        
        N+1 Problem: 
        - 1 query to get all posts
        - N queries to get author for each post
        
        Solution: Load related data in same/fewer queries
        """
        
        # joinedload: Single query with JOIN
        # Good for one-to-one and many-to-one
        stmt = (
            select(Post)
            .options(joinedload(Post.author))
            .where(Post.is_published == True)
        )
        
        # selectinload: Separate SELECT with IN clause
        # Good for one-to-many and many-to-many
        stmt = (
            select(User)
            .options(selectinload(User.posts))
        )
        
        # Multiple eager loads
        stmt = (
            select(Post)
            .options(
                joinedload(Post.author),
                selectinload(Post.tags),
                selectinload(Post.comments).joinedload(Comment.author)
            )
        )
        
        # contains_eager: Use with explicit join
        stmt = (
            select(Post)
            .join(Post.author)
            .options(contains_eager(Post.author))
            .where(User.is_active == True)
        )
        
        return session.execute(stmt).unique().scalars().all()
    
    # ============================================================
    # Subqueries
    # ============================================================
    
    @staticmethod
    def subquery_examples(session: Session):
        """Subquery patterns."""
        
        # Scalar subquery (returns single value)
        avg_price = (
            select(func.avg(Product.price))
            .scalar_subquery()
        )
        
        # Products above average price
        stmt = select(Product).where(Product.price > avg_price)
        
        # Correlated subquery
        # Users who have published posts
        post_subq = (
            select(Post.author_id)
            .where(Post.is_published == True)
            .correlate(User)
        )
        
        stmt = select(User).where(User.id.in_(post_subq))
        
        # EXISTS subquery
        has_posts = (
            select(Post)
            .where(Post.author_id == User.id)
            .exists()
        )
        
        stmt = select(User).where(has_posts)
        
        # Derived table (subquery in FROM)
        subq = (
            select(
                Product.category,
                func.avg(Product.price).label("avg_price")
            )
            .group_by(Product.category)
            .subquery()
        )
        
        stmt = (
            select(Product, subq.c.avg_price)
            .join(subq, Product.category == subq.c.category)
            .where(Product.price > subq.c.avg_price)
        )
        
        return session.execute(stmt).all()
    
    # ============================================================
    # CASE Expressions
    # ============================================================
    
    @staticmethod
    def case_examples(session: Session):
        """Conditional expressions."""
        
        # Simple CASE
        price_tier = case(
            (Product.price < 10, "budget"),
            (Product.price < 50, "mid-range"),
            (Product.price < 100, "premium"),
            else_="luxury"
        ).label("tier")
        
        stmt = select(Product.name, Product.price, price_tier)
        
        # CASE in aggregation
        stmt = (
            select(
                func.count(case((Product.stock > 0, 1))).label("in_stock"),
                func.count(case((Product.stock == 0, 1))).label("out_of_stock")
            )
        )
        
        # Conditional ordering
        stmt = (
            select(Product)
            .order_by(
                case(
                    (Product.stock > 0, 0),
                    else_=1
                ),
                Product.name
            )
        )
        
        return session.execute(stmt).all()
    
    # ============================================================
    # Window Functions (PostgreSQL)
    # ============================================================
    
    @staticmethod
    def window_function_examples(session: Session):
        """Window functions for analytics."""
        
        # Row number
        stmt = (
            select(
                Product.name,
                Product.price,
                Product.category,
                func.row_number().over(
                    partition_by=Product.category,
                    order_by=desc(Product.price)
                ).label("rank_in_category")
            )
        )
        
        # Running total
        stmt = (
            select(
                Product.name,
                Product.price,
                func.sum(Product.price).over(
                    order_by=Product.id
                ).label("running_total")
            )
        )
        
        # Rank within group
        stmt = (
            select(
                Product.name,
                Product.category,
                Product.price,
                func.rank().over(
                    partition_by=Product.category,
                    order_by=desc(Product.price)
                ).label("price_rank")
            )
        )
        
        return session.execute(stmt).all()
    
    # ============================================================
    # Raw SQL
    # ============================================================
    
    @staticmethod
    def raw_sql_examples(session: Session):
        """Execute raw SQL when needed."""
        
        # Simple raw SQL
        result = session.execute(text("SELECT * FROM products LIMIT 10"))
        
        # With parameters (SAFE - prevents SQL injection)
        result = session.execute(
            text("SELECT * FROM products WHERE category = :cat AND price > :price"),
            {"cat": "electronics", "price": 50}
        )
        
        # Hybrid: Raw SQL in ORM query
        stmt = (
            select(Product)
            .where(text("price > 100"))
            .order_by(text("price DESC"))
        )
        
        return session.execute(stmt).scalars().all()
