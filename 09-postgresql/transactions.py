"""
PostgreSQL Transactions with psycopg2
=====================================
Demonstrates transaction management, isolation levels, and error handling.
"""

import psycopg2
from psycopg2 import sql, errors
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Database Configuration
# =============================================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "demo_db",
    "user": "postgres",
    "password": "password",
}


# =============================================================================
# Connection Management
# =============================================================================

@contextmanager
def get_connection(**kwargs):
    """Context manager for database connections."""
    config = {**DB_CONFIG, **kwargs}
    conn = psycopg2.connect(**config)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(conn, cursor_factory=RealDictCursor):
    """Context manager for database cursors."""
    cursor = conn.cursor(cursor_factory=cursor_factory)
    try:
        yield cursor
    finally:
        cursor.close()


# =============================================================================
# Basic Transactions
# =============================================================================

def basic_transaction_example():
    """
    Basic transaction with commit and rollback.
    By default, psycopg2 starts a transaction on first command.
    """
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            try:
                # Execute multiple statements in a transaction
                cursor.execute("""
                    INSERT INTO products (name, slug, price, category_id) 
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, ("Test Product", "test-product", 99.99, 1))
                
                product_id = cursor.fetchone()["id"]
                logger.info(f"Inserted product with ID: {product_id}")
                
                cursor.execute("""
                    UPDATE products SET stock_quantity = %s WHERE id = %s
                """, (100, product_id))
                
                # Commit the transaction
                conn.commit()
                logger.info("Transaction committed successfully")
                
            except Exception as e:
                # Rollback on any error
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise


def autocommit_example():
    """
    Autocommit mode: Each statement is its own transaction.
    Useful for DDL commands or when you don't need transaction control.
    """
    with get_connection() as conn:
        conn.autocommit = True
        with get_cursor(conn) as cursor:
            # Each statement commits immediately
            cursor.execute("SELECT NOW()")
            result = cursor.fetchone()
            logger.info(f"Current time: {result['now']}")


# =============================================================================
# Isolation Levels
# =============================================================================

from psycopg2.extensions import (
    ISOLATION_LEVEL_AUTOCOMMIT,
    ISOLATION_LEVEL_READ_COMMITTED,
    ISOLATION_LEVEL_REPEATABLE_READ,
    ISOLATION_LEVEL_SERIALIZABLE,
)


def read_committed_example():
    """
    READ COMMITTED (default): Sees only committed data.
    Each query sees a snapshot at query start time.
    """
    with get_connection() as conn:
        conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        
        with get_cursor(conn) as cursor:
            # First read
            cursor.execute("SELECT COUNT(*) as count FROM products")
            count1 = cursor.fetchone()["count"]
            
            # Another transaction could commit here...
            
            # Second read might see different data
            cursor.execute("SELECT COUNT(*) as count FROM products")
            count2 = cursor.fetchone()["count"]
            
            logger.info(f"Count 1: {count1}, Count 2: {count2}")
            conn.commit()


def repeatable_read_example():
    """
    REPEATABLE READ: Consistent snapshot for entire transaction.
    All queries see data as of transaction start.
    """
    with get_connection() as conn:
        conn.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)
        
        with get_cursor(conn) as cursor:
            # First read establishes snapshot
            cursor.execute("SELECT COUNT(*) as count FROM products")
            count1 = cursor.fetchone()["count"]
            
            # Even if another transaction commits, we see same data
            cursor.execute("SELECT COUNT(*) as count FROM products")
            count2 = cursor.fetchone()["count"]
            
            # count1 == count2 guaranteed
            logger.info(f"Repeatable: Count 1: {count1}, Count 2: {count2}")
            conn.commit()


def serializable_example():
    """
    SERIALIZABLE: Strictest isolation level.
    Transactions appear to execute serially.
    May raise SerializationFailure errors requiring retry.
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
                
                with get_cursor(conn) as cursor:
                    # Read a value
                    cursor.execute("""
                        SELECT stock_quantity FROM products 
                        WHERE id = 1 FOR UPDATE
                    """)
                    row = cursor.fetchone()
                    
                    if row:
                        current_stock = row["stock_quantity"]
                        
                        # Update based on read
                        cursor.execute("""
                            UPDATE products 
                            SET stock_quantity = %s 
                            WHERE id = 1
                        """, (current_stock - 1,))
                        
                        conn.commit()
                        logger.info("Serializable transaction committed")
                        return
                        
        except errors.SerializationFailure:
            logger.warning(f"Serialization failure, attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise


# =============================================================================
# Savepoints
# =============================================================================

def savepoint_example():
    """
    Savepoints allow partial rollback within a transaction.
    """
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            try:
                # First operation
                cursor.execute("""
                    INSERT INTO categories (name, slug) 
                    VALUES (%s, %s) RETURNING id
                """, ("Category A", "category-a"))
                cat_a_id = cursor.fetchone()["id"]
                logger.info(f"Inserted Category A: {cat_a_id}")
                
                # Create savepoint
                cursor.execute("SAVEPOINT sp1")
                
                try:
                    # Second operation (might fail)
                    cursor.execute("""
                        INSERT INTO categories (name, slug) 
                        VALUES (%s, %s) RETURNING id
                    """, ("Category B", "category-a"))  # Duplicate slug!
                    
                except errors.UniqueViolation:
                    # Rollback to savepoint (keeps Category A)
                    cursor.execute("ROLLBACK TO SAVEPOINT sp1")
                    logger.warning("Rolled back to savepoint, Category A preserved")
                
                # Continue with another operation
                cursor.execute("""
                    INSERT INTO categories (name, slug) 
                    VALUES (%s, %s) RETURNING id
                """, ("Category C", "category-c"))
                cat_c_id = cursor.fetchone()["id"]
                logger.info(f"Inserted Category C: {cat_c_id}")
                
                # Commit entire transaction
                conn.commit()
                logger.info("Transaction committed with A and C")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                raise


# =============================================================================
# Row Locking
# =============================================================================

def pessimistic_locking_for_update():
    """
    SELECT ... FOR UPDATE locks rows for modification.
    Other transactions wait until lock is released.
    """
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            # Lock the product row
            cursor.execute("""
                SELECT id, stock_quantity 
                FROM products 
                WHERE id = 1 
                FOR UPDATE
            """)
            product = cursor.fetchone()
            
            if product and product["stock_quantity"] > 0:
                # Safe to update - row is locked
                cursor.execute("""
                    UPDATE products 
                    SET stock_quantity = stock_quantity - 1 
                    WHERE id = %s
                """, (product["id"],))
                
                conn.commit()
                logger.info("Stock decremented with FOR UPDATE lock")
            else:
                conn.rollback()
                logger.warning("Product not found or out of stock")


def pessimistic_locking_nowait():
    """
    FOR UPDATE NOWAIT fails immediately if row is locked.
    """
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            try:
                cursor.execute("""
                    SELECT id, stock_quantity 
                    FROM products 
                    WHERE id = 1 
                    FOR UPDATE NOWAIT
                """)
                product = cursor.fetchone()
                
                # Process if we got the lock
                if product:
                    cursor.execute("""
                        UPDATE products 
                        SET stock_quantity = stock_quantity - 1 
                        WHERE id = %s
                    """, (product["id"],))
                    conn.commit()
                    
            except errors.LockNotAvailable:
                conn.rollback()
                logger.warning("Could not acquire lock - row is locked by another transaction")


def pessimistic_locking_skip_locked():
    """
    FOR UPDATE SKIP LOCKED skips locked rows.
    Useful for work queues where multiple workers process items.
    """
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            # Get an unprocessed, unlocked order
            cursor.execute("""
                SELECT id, order_number 
                FROM orders 
                WHERE status = 'pending' 
                ORDER BY created_at 
                LIMIT 1 
                FOR UPDATE SKIP LOCKED
            """)
            order = cursor.fetchone()
            
            if order:
                logger.info(f"Processing order: {order['order_number']}")
                
                # Process the order
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'processing' 
                    WHERE id = %s
                """, (order["id"],))
                
                conn.commit()
            else:
                conn.rollback()
                logger.info("No available orders to process")


# =============================================================================
# Optimistic Locking (Version-based)
# =============================================================================

def optimistic_locking_example():
    """
    Optimistic locking uses a version column to detect conflicts.
    """
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            # Read with version
            cursor.execute("""
                SELECT id, name, stock_quantity, updated_at 
                FROM products 
                WHERE id = 1
            """)
            product = cursor.fetchone()
            
            if not product:
                logger.warning("Product not found")
                return
            
            original_updated_at = product["updated_at"]
            new_stock = product["stock_quantity"] - 1
            
            # Update only if version matches
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = %s, updated_at = NOW()
                WHERE id = %s AND updated_at = %s
                RETURNING id
            """, (new_stock, product["id"], original_updated_at))
            
            result = cursor.fetchone()
            
            if result:
                conn.commit()
                logger.info("Optimistic update succeeded")
            else:
                conn.rollback()
                logger.warning("Optimistic lock conflict - data was modified")
                # Could retry here


# =============================================================================
# Advisory Locks
# =============================================================================

def advisory_lock_example():
    """
    Advisory locks are application-level locks not tied to tables.
    Useful for coordinating processes.
    """
    LOCK_ID = 12345  # Application-defined lock identifier
    
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            # Try to acquire lock (non-blocking)
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,))
            acquired = cursor.fetchone()["pg_try_advisory_lock"]
            
            if acquired:
                try:
                    logger.info("Advisory lock acquired")
                    
                    # Do exclusive work here
                    cursor.execute("SELECT pg_sleep(2)")  # Simulate work
                    
                finally:
                    # Release the lock
                    cursor.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
                    logger.info("Advisory lock released")
            else:
                logger.warning("Could not acquire advisory lock")


def advisory_lock_blocking():
    """
    Blocking advisory lock - waits until lock is available.
    """
    LOCK_ID = 12345
    
    with get_connection() as conn:
        with get_cursor(conn) as cursor:
            # This will block until lock is available
            cursor.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
            logger.info("Advisory lock acquired (was blocking)")
            
            try:
                # Critical section
                pass
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))


# =============================================================================
# Transaction Decorator
# =============================================================================

def transactional(isolation_level=ISOLATION_LEVEL_READ_COMMITTED):
    """Decorator for transactional methods."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with get_connection() as conn:
                conn.set_isolation_level(isolation_level)
                try:
                    result = func(conn, *args, **kwargs)
                    conn.commit()
                    return result
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Transaction failed: {e}")
                    raise
        return wrapper
    return decorator


@transactional(isolation_level=ISOLATION_LEVEL_REPEATABLE_READ)
def transfer_money(conn, from_account: int, to_account: int, amount: float):
    """Example of using the transactional decorator."""
    with get_cursor(conn) as cursor:
        # Debit from source
        cursor.execute("""
            UPDATE accounts SET balance = balance - %s 
            WHERE id = %s AND balance >= %s
            RETURNING balance
        """, (amount, from_account, amount))
        
        if not cursor.fetchone():
            raise ValueError("Insufficient funds or account not found")
        
        # Credit to destination
        cursor.execute("""
            UPDATE accounts SET balance = balance + %s 
            WHERE id = %s
            RETURNING balance
        """, (amount, to_account))
        
        if not cursor.fetchone():
            raise ValueError("Destination account not found")
        
        logger.info(f"Transferred {amount} from {from_account} to {to_account}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("PostgreSQL Transactions Demo")
    print("=" * 50)
    print("""
    This module demonstrates PostgreSQL transaction patterns:
    
    1. Basic Transactions
       - basic_transaction_example()
       - autocommit_example()
    
    2. Isolation Levels
       - read_committed_example()
       - repeatable_read_example()
       - serializable_example()
    
    3. Savepoints
       - savepoint_example()
    
    4. Row Locking (Pessimistic)
       - pessimistic_locking_for_update()
       - pessimistic_locking_nowait()
       - pessimistic_locking_skip_locked()
    
    5. Optimistic Locking
       - optimistic_locking_example()
    
    6. Advisory Locks
       - advisory_lock_example()
       - advisory_lock_blocking()
    
    7. Transaction Decorator
       - @transactional decorator
    
    To run examples, set up DB_CONFIG and run:
        python transactions.py
    """)
