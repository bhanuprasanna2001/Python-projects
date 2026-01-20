"""
Redis Caching Patterns
======================
Common caching strategies with Redis.
"""

import redis
import json
import time
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
from datetime import timedelta


def get_redis_client() -> redis.Redis:
    return redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


# =============================================================================
# Cache-Aside Pattern
# =============================================================================

class CacheAside:
    """
    Cache-Aside (Lazy Loading) Pattern
    
    Read:  App -> Cache (miss) -> Database -> Cache -> App
    Write: App -> Database -> Invalidate Cache
    """
    
    def __init__(self, redis_client: redis.Redis, default_ttl: int = 300):
        self.redis = redis_client
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.redis.get(f"cache:{key}")
        if value:
            return json.loads(value)
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache."""
        self.redis.setex(
            f"cache:{key}",
            ttl or self.default_ttl,
            json.dumps(value)
        )
    
    def delete(self, key: str) -> None:
        """Invalidate cache entry."""
        self.redis.delete(f"cache:{key}")
    
    def get_or_set(
        self,
        key: str,
        fetch_func: Callable,
        ttl: int = None
    ) -> Any:
        """Get from cache or fetch and cache."""
        # Try cache first
        cached = self.get(key)
        if cached is not None:
            print(f"Cache HIT: {key}")
            return cached
        
        # Cache miss - fetch from source
        print(f"Cache MISS: {key}")
        value = fetch_func()
        
        # Store in cache
        self.set(key, value, ttl)
        
        return value


def cache_aside_example():
    """Demonstrate cache-aside pattern."""
    print("\n=== Cache-Aside Pattern ===\n")
    
    r = get_redis_client()
    cache = CacheAside(r)
    
    # Simulate database fetch
    def fetch_user(user_id: int):
        print(f"  Fetching user {user_id} from database...")
        time.sleep(0.1)  # Simulate DB latency
        return {"id": user_id, "name": f"User {user_id}"}
    
    # First call - cache miss
    user = cache.get_or_set("user:123", lambda: fetch_user(123))
    print(f"  User: {user}")
    
    # Second call - cache hit
    user = cache.get_or_set("user:123", lambda: fetch_user(123))
    print(f"  User: {user}")
    
    # Invalidate on update
    cache.delete("user:123")
    print("  Cache invalidated")
    
    # Next call - cache miss again
    user = cache.get_or_set("user:123", lambda: fetch_user(123))
    print(f"  User: {user}")


# =============================================================================
# Write-Through Pattern
# =============================================================================

class WriteThrough:
    """
    Write-Through Pattern
    
    Write: App -> Cache -> Database (synchronous)
    Read:  App -> Cache (always hit if written)
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def write(self, key: str, value: Any, db_write_func: Callable) -> bool:
        """Write to cache and database."""
        try:
            # Write to database first
            db_write_func(value)
            
            # Then update cache
            self.redis.set(f"cache:{key}", json.dumps(value))
            
            return True
        except Exception as e:
            print(f"Write failed: {e}")
            return False
    
    def read(self, key: str) -> Optional[Any]:
        """Read from cache."""
        value = self.redis.get(f"cache:{key}")
        if value:
            return json.loads(value)
        return None


# =============================================================================
# Write-Behind (Write-Back) Pattern
# =============================================================================

class WriteBehind:
    """
    Write-Behind Pattern
    
    Write: App -> Cache -> Return (async write to DB later)
    
    Good for write-heavy workloads but risks data loss.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.write_queue = "cache:write_queue"
    
    def write(self, key: str, value: Any) -> None:
        """Write to cache and queue for DB persistence."""
        # Immediate cache update
        self.redis.set(f"cache:{key}", json.dumps(value))
        
        # Queue for async DB write
        self.redis.rpush(self.write_queue, json.dumps({
            "key": key,
            "value": value,
            "timestamp": time.time(),
        }))
    
    def process_write_queue(self, db_write_func: Callable) -> int:
        """Process queued writes (run in background worker)."""
        processed = 0
        
        while True:
            # Get next item from queue
            item = self.redis.lpop(self.write_queue)
            if not item:
                break
            
            data = json.loads(item)
            try:
                db_write_func(data["key"], data["value"])
                processed += 1
            except Exception as e:
                # Re-queue failed writes
                self.redis.rpush(self.write_queue, item)
                print(f"Write failed, re-queued: {e}")
                break
        
        return processed


# =============================================================================
# Memoization Decorator
# =============================================================================

def memoize(
    ttl: int = 300,
    prefix: str = "memo",
    redis_client: redis.Redis = None
):
    """
    Decorator for caching function results.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = redis_client or get_redis_client()
            
            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
            
            # Try cache
            cached = client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        
        # Add cache invalidation method
        def invalidate(*args, **kwargs):
            client = redis_client or get_redis_client()
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
            client.delete(cache_key)
        
        wrapper.invalidate = invalidate
        return wrapper
    
    return decorator


def memoize_example():
    """Demonstrate memoization decorator."""
    print("\n=== Memoization Decorator ===\n")
    
    @memoize(ttl=60)
    def expensive_calculation(x: int, y: int) -> int:
        print(f"  Computing {x} + {y}...")
        time.sleep(0.5)  # Simulate expensive operation
        return x + y
    
    # First call - computed
    result = expensive_calculation(5, 3)
    print(f"  Result: {result}")
    
    # Second call - cached
    result = expensive_calculation(5, 3)
    print(f"  Result: {result}")
    
    # Invalidate
    expensive_calculation.invalidate(5, 3)
    print("  Cache invalidated")
    
    # Third call - computed again
    result = expensive_calculation(5, 3)
    print(f"  Result: {result}")


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    Token bucket rate limiter using Redis.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "ratelimit",
        max_requests: int = 10,
        window_seconds: int = 60
    ):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        Returns (allowed, remaining_requests).
        """
        key = f"{self.key_prefix}:{identifier}"
        
        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Increment counter
        pipe.incr(key)
        
        # Set expiry if new key
        pipe.expire(key, self.window_seconds)
        
        results = pipe.execute()
        current_count = results[0]
        
        remaining = max(0, self.max_requests - current_count)
        allowed = current_count <= self.max_requests
        
        return allowed, remaining
    
    def get_wait_time(self, identifier: str) -> int:
        """Get seconds until rate limit resets."""
        key = f"{self.key_prefix}:{identifier}"
        ttl = self.redis.ttl(key)
        return max(0, ttl)


class SlidingWindowRateLimiter:
    """
    More accurate sliding window rate limiter.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "ratelimit_sw",
        max_requests: int = 10,
        window_seconds: int = 60
    ):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed using sliding window."""
        key = f"{self.key_prefix}:{identifier}"
        now = time.time()
        window_start = now - self.window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, '-inf', window_start)
        
        # Count current entries
        pipe.zcard(key)
        
        # Add new entry
        pipe.zadd(key, {str(now): now})
        
        # Set expiry
        pipe.expire(key, self.window_seconds)
        
        results = pipe.execute()
        current_count = results[1]
        
        remaining = max(0, self.max_requests - current_count - 1)
        allowed = current_count < self.max_requests
        
        return allowed, remaining


def rate_limit_example():
    """Demonstrate rate limiting."""
    print("\n=== Rate Limiting ===\n")
    
    r = get_redis_client()
    limiter = RateLimiter(r, max_requests=5, window_seconds=10)
    
    user_id = "user:123"
    
    for i in range(8):
        allowed, remaining = limiter.is_allowed(user_id)
        print(f"  Request {i+1}: {'Allowed' if allowed else 'Blocked'}, Remaining: {remaining}")
        time.sleep(0.5)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Redis Caching Patterns")
    print("=" * 60)
    
    cache_aside_example()
    memoize_example()
    rate_limit_example()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
