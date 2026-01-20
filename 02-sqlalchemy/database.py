"""
Database Configuration
======================
Engine, session, and connection pool setup.
Demonstrates both sync and async configurations.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

# SQLite for demo (easy setup, no external DB needed)
# For PostgreSQL: "postgresql://user:pass@localhost:5432/dbname"
DATABASE_URL = "sqlite:///./demo.db"
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./demo_async.db"

# ============================================================
# Sync Engine Configuration
# ============================================================

engine = create_engine(
    DATABASE_URL,
    # Connection pool settings (for PostgreSQL/MySQL)
    # poolclass=QueuePool,
    # pool_size=5,           # Number of connections to keep
    # max_overflow=10,       # Extra connections when pool exhausted
    # pool_timeout=30,       # Seconds to wait for connection
    # pool_recycle=1800,     # Recycle connections after 30 min
    echo=True,  # Log SQL statements (disable in production)
    future=True  # Use SQLAlchemy 2.0 style
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # Require explicit commit
    autoflush=False,   # Don't auto-flush before queries
    expire_on_commit=False  # Don't expire objects after commit
)

# Base class for models
Base = declarative_base()


# ============================================================
# Connection Event Listeners
# ============================================================

@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """Called when a new connection is created."""
    print(f"[DB] New connection established")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Called when a connection is retrieved from the pool."""
    print(f"[DB] Connection checked out from pool")


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """Called when a connection is returned to the pool."""
    print(f"[DB] Connection returned to pool")


# ============================================================
# Session Management
# ============================================================

@contextmanager
def get_session():
    """
    Context manager for session handling.
    Ensures proper commit/rollback and cleanup.
    
    Usage:
        with get_session() as session:
            session.add(user)
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_db():
    """
    Dependency for FastAPI.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# Database Initialization
# ============================================================

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created successfully")


def drop_db():
    """Drop all tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)
    print("[DB] Tables dropped")


def reset_db():
    """Reset database (drop and recreate)."""
    drop_db()
    init_db()


# ============================================================
# Async Configuration (SQLAlchemy 2.0)
# ============================================================

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_async_session():
    """Async session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_async_db():
    """Create tables asynchronously."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
