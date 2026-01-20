"""
SQLAlchemy Demo
===============
Interactive demonstration of SQLAlchemy features.
"""

from database import init_db, reset_db, get_session, SessionLocal
from models import User, Post, Tag, Comment, Product, Role, UserRole, Profile
from crud import UserCRUD, PostCRUD, ProductCRUD
from queries import QueryExamples
from datetime import datetime
import random


def seed_data(session):
    """Populate database with sample data."""
    print("\n" + "=" * 50)
    print("Seeding database...")
    print("=" * 50)
    
    # Create roles
    roles = [
        Role(name="admin", description="Full access"),
        Role(name="editor", description="Can edit content"),
        Role(name="viewer", description="Read-only access")
    ]
    session.add_all(roles)
    session.flush()
    
    # Create tags
    tags = [
        Tag(name="Python", slug="python", description="Python programming"),
        Tag(name="FastAPI", slug="fastapi", description="FastAPI framework"),
        Tag(name="SQLAlchemy", slug="sqlalchemy", description="SQL toolkit"),
        Tag(name="Database", slug="database", description="Database topics"),
        Tag(name="Tutorial", slug="tutorial", description="Tutorial content")
    ]
    session.add_all(tags)
    session.flush()
    
    # Create users with profiles
    users = []
    for i in range(5):
        user = User(
            username=f"user{i+1}",
            email=f"user{i+1}@example.com",
            password_hash=f"hashed_password_{i+1}",
            full_name=f"User {i+1}",
            bio=f"Bio for user {i+1}"
        )
        users.append(user)
        session.add(user)
    
    session.flush()
    
    # Add profiles
    for user in users:
        profile = Profile(
            user_id=user.id,
            website=f"https://user{user.id}.com",
            location="City"
        )
        session.add(profile)
    
    # Assign roles to users
    for user in users[:2]:  # First 2 users are admins
        user_role = UserRole(user_id=user.id, role_id=roles[0].id)
        session.add(user_role)
    
    # Create posts with tags
    for i, user in enumerate(users):
        for j in range(3):
            post = Post(
                title=f"Post {i*3 + j + 1} by {user.username}",
                slug=f"post-{i*3 + j + 1}",
                content=f"Content of post {i*3 + j + 1}",
                author_id=user.id,
                is_published=random.choice([True, True, False]),
                view_count=random.randint(0, 1000)
            )
            # Assign random tags
            post.tags = random.sample(tags, random.randint(1, 3))
            session.add(post)
    
    session.flush()
    
    # Create products
    categories = ["electronics", "books", "clothing", "food", "toys"]
    products = []
    for i in range(20):
        product = Product(
            name=f"Product {i+1}",
            description=f"Description for product {i+1}",
            price=round(random.uniform(5, 500), 2),
            stock=random.randint(0, 100),
            category=random.choice(categories),
            is_active=random.choice([True, True, True, False])
        )
        products.append(product)
    
    session.add_all(products)
    session.commit()
    
    print(f"Created {len(users)} users")
    print(f"Created {len(roles)} roles")
    print(f"Created {len(tags)} tags")
    print(f"Created {len(users) * 3} posts")
    print(f"Created {len(products)} products")


def demo_crud_operations():
    """Demonstrate CRUD operations."""
    print("\n" + "=" * 50)
    print("CRUD Operations Demo")
    print("=" * 50)
    
    with get_session() as session:
        # CREATE
        print("\n--- CREATE ---")
        new_user = UserCRUD.create(
            session,
            username="new_user",
            email="new@example.com",
            password_hash="hashed_pwd"
        )
        print(f"Created: {new_user}")
        
        # READ
        print("\n--- READ ---")
        user = UserCRUD.get_by_username(session, "user1")
        print(f"Found user: {user}")
        
        all_users = UserCRUD.get_all(session, limit=5)
        print(f"Total active users: {len(all_users)}")
        
        # UPDATE
        print("\n--- UPDATE ---")
        if user:
            UserCRUD.update(session, user, full_name="Updated Name")
            print(f"Updated user: {user.full_name}")
        
        # DELETE (soft)
        print("\n--- SOFT DELETE ---")
        if new_user:
            UserCRUD.soft_delete(session, new_user)
            print(f"Soft deleted user: {new_user.is_active}")


def demo_relationships():
    """Demonstrate relationship handling."""
    print("\n" + "=" * 50)
    print("Relationships Demo")
    print("=" * 50)
    
    with get_session() as session:
        # One-to-Many: User -> Posts
        print("\n--- One-to-Many (User -> Posts) ---")
        user = UserCRUD.get_by_username(session, "user1")
        if user:
            print(f"User: {user.username}")
            posts = user.posts.limit(3).all()
            for post in posts:
                print(f"  - {post.title}")
        
        # One-to-One: User -> Profile
        print("\n--- One-to-One (User -> Profile) ---")
        if user and user.profile:
            print(f"Profile website: {user.profile.website}")
        
        # Many-to-Many: Post -> Tags
        print("\n--- Many-to-Many (Post -> Tags) ---")
        post = session.query(Post).first()
        if post:
            print(f"Post: {post.title}")
            print(f"Tags: {[tag.name for tag in post.tags]}")
        
        # Reverse Many-to-Many: Tag -> Posts
        print("\n--- Reverse Many-to-Many (Tag -> Posts) ---")
        tag = session.query(Tag).filter(Tag.name == "Python").first()
        if tag:
            print(f"Tag '{tag.name}' has {len(tag.posts)} posts")


def demo_queries():
    """Demonstrate advanced queries."""
    print("\n" + "=" * 50)
    print("Advanced Queries Demo")
    print("=" * 50)
    
    with get_session() as session:
        # Aggregations
        print("\n--- Aggregations ---")
        stats = QueryExamples.aggregation_examples(session)
        print(f"Product stats: {stats}")
        
        # Group By
        print("\n--- Group By ---")
        from sqlalchemy import select, func, desc
        
        stmt = (
            select(
                Product.category,
                func.count().label("count"),
                func.avg(Product.price).label("avg_price")
            )
            .group_by(Product.category)
            .order_by(desc("count"))
        )
        
        results = session.execute(stmt).all()
        print("Products by category:")
        for cat, count, avg in results:
            print(f"  {cat}: {count} products, avg price: ${avg:.2f}")
        
        # Complex filter
        print("\n--- Complex Filtering ---")
        from sqlalchemy import and_, or_
        
        stmt = (
            select(Product)
            .where(
                and_(
                    Product.is_active == True,
                    or_(
                        Product.price < 20,
                        Product.stock > 50
                    )
                )
            )
            .limit(5)
        )
        
        products = session.execute(stmt).scalars().all()
        print(f"Found {len(products)} matching products")


def demo_eager_loading():
    """Demonstrate eager loading to prevent N+1."""
    print("\n" + "=" * 50)
    print("Eager Loading Demo (N+1 Prevention)")
    print("=" * 50)
    
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload, selectinload
    
    with get_session() as session:
        # Without eager loading (N+1 problem)
        print("\n--- Without Eager Loading (N+1) ---")
        print("This would cause N+1 queries in production!")
        
        # With eager loading
        print("\n--- With joinedload (Single JOIN query) ---")
        stmt = (
            select(Post)
            .options(joinedload(Post.author))
            .where(Post.is_published == True)
            .limit(5)
        )
        
        posts = session.execute(stmt).unique().scalars().all()
        for post in posts:
            print(f"  {post.title} by {post.author.username}")
        
        print("\n--- With selectinload (Separate IN query) ---")
        stmt = (
            select(User)
            .options(selectinload(User.posts))
            .limit(3)
        )
        
        users = session.execute(stmt).scalars().all()
        for user in users:
            print(f"  {user.username}: {len(list(user.posts))} posts")


def demo_transactions():
    """Demonstrate transaction handling."""
    print("\n" + "=" * 50)
    print("Transaction Demo")
    print("=" * 50)
    
    session = SessionLocal()
    
    try:
        print("\n--- Starting transaction ---")
        
        # Create product
        product = Product(
            name="Transaction Test",
            price=99.99,
            stock=10,
            category="test"
        )
        session.add(product)
        session.flush()  # Get ID without committing
        print(f"Created product with ID: {product.id}")
        
        # Simulate some operations
        product.stock -= 5
        print(f"Updated stock to: {product.stock}")
        
        # Commit transaction
        session.commit()
        print("Transaction committed!")
        
    except Exception as e:
        session.rollback()
        print(f"Transaction rolled back: {e}")
    
    finally:
        session.close()
    
    # Demo: Intentional rollback
    print("\n--- Intentional Rollback ---")
    session = SessionLocal()
    
    try:
        product = Product(name="Will be rolled back", price=50, stock=5, category="test")
        session.add(product)
        session.flush()
        print(f"Created product ID: {product.id}")
        
        # Intentionally rollback
        session.rollback()
        print("Rolled back - product not saved")
        
    finally:
        session.close()


def main():
    """Main entry point."""
    print("=" * 50)
    print("SQLAlchemy ORM Demo")
    print("=" * 50)
    
    # Reset and initialize database
    reset_db()
    
    # Seed with sample data
    with get_session() as session:
        seed_data(session)
    
    # Run demos
    demo_crud_operations()
    demo_relationships()
    demo_queries()
    demo_eager_loading()
    demo_transactions()
    
    print("\n" + "=" * 50)
    print("Demo completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
