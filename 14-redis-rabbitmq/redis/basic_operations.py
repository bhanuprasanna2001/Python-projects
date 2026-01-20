"""
Redis Basic Operations
======================
Demonstrates fundamental Redis commands and operations.
"""

import redis
from datetime import timedelta
import json
from typing import Optional, Any


# =============================================================================
# Connection
# =============================================================================

def get_redis_client() -> redis.Redis:
    """Create Redis client."""
    return redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,  # Return strings instead of bytes
    )


# =============================================================================
# String Operations
# =============================================================================

def string_operations():
    """Basic string operations."""
    print("\n=== String Operations ===\n")
    
    r = get_redis_client()
    
    # SET - Store a value
    r.set("user:1:name", "John Doe")
    print(f"SET user:1:name = 'John Doe'")
    
    # GET - Retrieve a value
    name = r.get("user:1:name")
    print(f"GET user:1:name = '{name}'")
    
    # SET with expiration
    r.set("session:abc123", "user_data", ex=3600)  # 1 hour
    print("SET session:abc123 with 1 hour expiration")
    
    # SETEX - Set with expiration (alternative)
    r.setex("cache:api:response", timedelta(minutes=5), "cached_data")
    print("SETEX cache:api:response with 5 minute expiration")
    
    # SETNX - Set only if not exists
    created = r.setnx("user:1:email", "john@example.com")
    print(f"SETNX user:1:email = {created} (True = created, False = existed)")
    
    # MSET - Set multiple keys
    r.mset({
        "user:2:name": "Jane Doe",
        "user:2:email": "jane@example.com",
        "user:2:age": "25",
    })
    print("MSET multiple keys")
    
    # MGET - Get multiple keys
    values = r.mget("user:2:name", "user:2:email", "user:2:age")
    print(f"MGET values = {values}")
    
    # INCR/DECR - Increment/Decrement
    r.set("counter:visits", "0")
    r.incr("counter:visits")
    r.incr("counter:visits")
    r.incrby("counter:visits", 10)
    visits = r.get("counter:visits")
    print(f"Counter after increments: {visits}")
    
    # APPEND
    r.set("message", "Hello")
    r.append("message", " World!")
    message = r.get("message")
    print(f"After APPEND: '{message}'")
    
    # GETRANGE - Get substring
    substring = r.getrange("message", 0, 4)
    print(f"GETRANGE 0-4: '{substring}'")
    
    # STRLEN
    length = r.strlen("message")
    print(f"STRLEN: {length}")


# =============================================================================
# Key Operations
# =============================================================================

def key_operations():
    """Key management operations."""
    print("\n=== Key Operations ===\n")
    
    r = get_redis_client()
    
    # Setup some keys
    r.set("test:key1", "value1")
    r.set("test:key2", "value2")
    r.set("test:key3", "value3")
    
    # EXISTS - Check if key exists
    exists = r.exists("test:key1")
    print(f"EXISTS test:key1 = {exists}")
    
    # Check multiple keys
    count = r.exists("test:key1", "test:key2", "test:nonexistent")
    print(f"EXISTS count (3 keys) = {count}")
    
    # KEYS - Find keys matching pattern (use sparingly in production!)
    keys = r.keys("test:*")
    print(f"KEYS test:* = {keys}")
    
    # SCAN - Iterate over keys (safer than KEYS)
    cursor = 0
    all_keys = []
    while True:
        cursor, keys = r.scan(cursor, match="test:*", count=100)
        all_keys.extend(keys)
        if cursor == 0:
            break
    print(f"SCAN test:* = {all_keys}")
    
    # TYPE - Get key type
    key_type = r.type("test:key1")
    print(f"TYPE test:key1 = {key_type}")
    
    # TTL - Get time to live
    r.expire("test:key1", 60)
    ttl = r.ttl("test:key1")
    print(f"TTL test:key1 = {ttl} seconds")
    
    # PERSIST - Remove expiration
    r.persist("test:key1")
    ttl = r.ttl("test:key1")
    print(f"TTL after PERSIST = {ttl} (-1 = no expiration)")
    
    # RENAME
    r.rename("test:key1", "test:key1_renamed")
    print("RENAME test:key1 -> test:key1_renamed")
    
    # DEL - Delete keys
    deleted = r.delete("test:key1_renamed", "test:key2")
    print(f"DEL deleted {deleted} keys")
    
    # UNLINK - Delete keys asynchronously (non-blocking)
    r.set("large:key", "x" * 1000)
    r.unlink("large:key")
    print("UNLINK large:key (async delete)")


# =============================================================================
# JSON Storage
# =============================================================================

def json_storage():
    """Storing JSON data in Redis."""
    print("\n=== JSON Storage ===\n")
    
    r = get_redis_client()
    
    # Store JSON object
    user_data = {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "preferences": {
            "theme": "dark",
            "notifications": True,
        },
        "tags": ["admin", "premium"],
    }
    
    # Method 1: Serialize entire object
    r.set("user:1:data", json.dumps(user_data))
    print("Stored user data as JSON string")
    
    # Retrieve and parse
    stored = r.get("user:1:data")
    parsed = json.loads(stored)
    print(f"Retrieved: {parsed['name']}")
    
    # Method 2: Use Hash for flat objects (better for partial updates)
    r.hset("user:2", mapping={
        "id": "2",
        "name": "Jane Doe",
        "email": "jane@example.com",
        "theme": "light",
    })
    print("Stored user as Hash")
    
    # Get all fields
    user_hash = r.hgetall("user:2")
    print(f"Hash data: {user_hash}")


# =============================================================================
# Pipeline (Batching)
# =============================================================================

def pipeline_operations():
    """Using pipelines for batched operations."""
    print("\n=== Pipeline Operations ===\n")
    
    r = get_redis_client()
    
    # Without pipeline (multiple round trips)
    import time
    
    start = time.time()
    for i in range(100):
        r.set(f"no_pipe:{i}", f"value_{i}")
    no_pipe_time = time.time() - start
    print(f"Without pipeline: {no_pipe_time:.3f}s for 100 operations")
    
    # With pipeline (single round trip)
    start = time.time()
    pipe = r.pipeline()
    for i in range(100):
        pipe.set(f"pipe:{i}", f"value_{i}")
    pipe.execute()
    pipe_time = time.time() - start
    print(f"With pipeline: {pipe_time:.3f}s for 100 operations")
    print(f"Speedup: {no_pipe_time / pipe_time:.1f}x")
    
    # Pipeline with transactions (atomic)
    pipe = r.pipeline(transaction=True)
    pipe.set("tx:counter", "0")
    pipe.incr("tx:counter")
    pipe.incr("tx:counter")
    results = pipe.execute()
    print(f"Transaction results: {results}")
    
    # Cleanup
    for i in range(100):
        r.delete(f"no_pipe:{i}", f"pipe:{i}")


# =============================================================================
# Transactions
# =============================================================================

def transaction_operations():
    """Redis transactions with WATCH."""
    print("\n=== Transaction Operations ===\n")
    
    r = get_redis_client()
    
    # Set initial value
    r.set("account:balance", "1000")
    
    # Optimistic locking with WATCH
    def transfer_funds(amount: int):
        """Transfer funds with optimistic locking."""
        with r.pipeline() as pipe:
            while True:
                try:
                    # Watch the key
                    pipe.watch("account:balance")
                    
                    # Read current balance
                    balance = int(pipe.get("account:balance"))
                    
                    if balance < amount:
                        pipe.unwatch()
                        return False, "Insufficient funds"
                    
                    # Start transaction
                    pipe.multi()
                    pipe.set("account:balance", balance - amount)
                    
                    # Execute (will fail if balance changed)
                    pipe.execute()
                    return True, f"Transferred {amount}"
                    
                except redis.WatchError:
                    # Someone else modified the balance
                    continue
    
    success, message = transfer_funds(100)
    print(f"Transfer result: {success}, {message}")
    print(f"New balance: {r.get('account:balance')}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Redis Basic Operations")
    print("=" * 60)
    
    string_operations()
    key_operations()
    json_storage()
    pipeline_operations()
    transaction_operations()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
