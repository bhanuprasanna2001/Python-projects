"""
Rate Limiting Patterns
======================
Various rate limiting algorithms implementation.
"""

import time
import threading
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple
import asyncio


# =============================================================================
# Base Rate Limiter Interface
# =============================================================================

class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if allowed."""
        pass
    
    @abstractmethod
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait before tokens are available."""
        pass


# =============================================================================
# Token Bucket Algorithm
# =============================================================================

class TokenBucket(RateLimiter):
    """
    Token Bucket rate limiter.
    
    - Tokens are added at a fixed rate
    - Bucket has maximum capacity
    - Allows bursts up to bucket capacity
    
    Example: 10 tokens/second with bucket of 20
    - Normal rate: 10 req/sec
    - Can burst up to 20 requests at once
    """
    
    def __init__(
        self,
        rate: float,           # Tokens per second
        capacity: int,         # Maximum bucket size
        initial_tokens: Optional[int] = None
    ):
        self.rate = rate
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_update = time.monotonic()
        self._lock = threading.Lock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens."""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait for tokens to be available."""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            needed = tokens - self.tokens
            return needed / self.rate
    
    def wait_and_acquire(self, tokens: int = 1) -> float:
        """Wait until tokens are available and acquire them."""
        wait_time = self.get_wait_time(tokens)
        if wait_time > 0:
            time.sleep(wait_time)
        
        # Acquire after waiting
        while not self.acquire(tokens):
            time.sleep(0.01)
        
        return wait_time


# =============================================================================
# Sliding Window Log Algorithm
# =============================================================================

class SlidingWindowLog(RateLimiter):
    """
    Sliding Window Log rate limiter.
    
    - Tracks timestamps of all requests in window
    - Most accurate but memory intensive
    - Window slides with time
    """
    
    def __init__(
        self,
        limit: int,           # Maximum requests
        window_seconds: float  # Window size in seconds
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self._lock = threading.Lock()
    
    def _cleanup(self) -> None:
        """Remove expired timestamps."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire (tokens = number of requests)."""
        with self._lock:
            self._cleanup()
            
            if len(self.requests) + tokens <= self.limit:
                now = time.monotonic()
                for _ in range(tokens):
                    self.requests.append(now)
                return True
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait until a slot is available."""
        with self._lock:
            self._cleanup()
            
            if len(self.requests) + tokens <= self.limit:
                return 0.0
            
            # Calculate when oldest request will expire
            if self.requests:
                oldest = self.requests[0]
                now = time.monotonic()
                return max(0, (oldest + self.window_seconds) - now)
            return 0.0
    
    def current_count(self) -> int:
        """Get current request count in window."""
        with self._lock:
            self._cleanup()
            return len(self.requests)


# =============================================================================
# Sliding Window Counter Algorithm
# =============================================================================

class SlidingWindowCounter(RateLimiter):
    """
    Sliding Window Counter rate limiter.
    
    - Compromise between fixed window and sliding log
    - Uses weighted average of current and previous window
    - Memory efficient with reasonable accuracy
    """
    
    def __init__(
        self,
        limit: int,
        window_seconds: float
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.current_window_count = 0
        self.previous_window_count = 0
        self.current_window_start = time.monotonic()
        self._lock = threading.Lock()
    
    def _get_window(self) -> Tuple[int, int, float]:
        """Get current state and position in window."""
        now = time.monotonic()
        window_start = self.current_window_start
        
        # Check if we need to roll to new window
        if now >= window_start + self.window_seconds:
            # Move to new window
            windows_passed = int((now - window_start) / self.window_seconds)
            
            if windows_passed == 1:
                self.previous_window_count = self.current_window_count
            else:
                self.previous_window_count = 0
            
            self.current_window_count = 0
            self.current_window_start = window_start + (windows_passed * self.window_seconds)
            window_start = self.current_window_start
        
        # Calculate position in current window (0.0 to 1.0)
        position = (now - window_start) / self.window_seconds
        
        return self.current_window_count, self.previous_window_count, position
    
    def _estimated_count(self) -> float:
        """Get weighted estimate of requests in sliding window."""
        current, previous, position = self._get_window()
        # Weight previous window by how much of it is still in our window
        return current + previous * (1 - position)
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens."""
        with self._lock:
            estimated = self._estimated_count()
            
            if estimated + tokens <= self.limit:
                self.current_window_count += tokens
                return True
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Estimate wait time."""
        with self._lock:
            estimated = self._estimated_count()
            
            if estimated + tokens <= self.limit:
                return 0.0
            
            # Rough estimate: wait for some of previous window to expire
            _, previous, position = self._get_window()
            excess = estimated + tokens - self.limit
            
            if previous > 0:
                # Time for enough of previous window to expire
                return min(self.window_seconds * (1 - position), self.window_seconds)
            return self.window_seconds


# =============================================================================
# Fixed Window Counter
# =============================================================================

class FixedWindowCounter(RateLimiter):
    """
    Fixed Window Counter rate limiter.
    
    - Simple counter reset at window boundaries
    - Can allow 2x rate at window boundaries
    - Very memory efficient
    """
    
    def __init__(
        self,
        limit: int,
        window_seconds: float
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.count = 0
        self.window_start = time.monotonic()
        self._lock = threading.Lock()
    
    def _check_window(self) -> None:
        """Reset counter if window has passed."""
        now = time.monotonic()
        if now >= self.window_start + self.window_seconds:
            self.count = 0
            self.window_start = now
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens."""
        with self._lock:
            self._check_window()
            
            if self.count + tokens <= self.limit:
                self.count += tokens
                return True
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time until window resets."""
        with self._lock:
            self._check_window()
            
            if self.count + tokens <= self.limit:
                return 0.0
            
            now = time.monotonic()
            return self.window_start + self.window_seconds - now


# =============================================================================
# Leaky Bucket Algorithm
# =============================================================================

class LeakyBucket(RateLimiter):
    """
    Leaky Bucket rate limiter.
    
    - Requests queue up in bucket
    - Bucket leaks at constant rate
    - Smooths out traffic
    """
    
    def __init__(
        self,
        rate: float,      # Leak rate (requests per second)
        capacity: int     # Maximum queue size
    ):
        self.rate = rate
        self.capacity = capacity
        self.water = 0.0  # Current water level
        self.last_leak = time.monotonic()
        self._lock = threading.Lock()
    
    def _leak(self) -> None:
        """Leak water based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_leak
        leaked = elapsed * self.rate
        self.water = max(0, self.water - leaked)
        self.last_leak = now
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to add water (request) to bucket."""
        with self._lock:
            self._leak()
            
            if self.water + tokens <= self.capacity:
                self.water += tokens
                return True
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait for space in bucket."""
        with self._lock:
            self._leak()
            
            if self.water + tokens <= self.capacity:
                return 0.0
            
            excess = self.water + tokens - self.capacity
            return excess / self.rate


# =============================================================================
# Async Rate Limiter Wrapper
# =============================================================================

class AsyncRateLimiter:
    """Async wrapper for any rate limiter."""
    
    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Async acquire."""
        async with self._lock:
            return self.limiter.acquire(tokens)
    
    async def wait_and_acquire(self, tokens: int = 1) -> float:
        """Wait and acquire asynchronously."""
        while True:
            async with self._lock:
                if self.limiter.acquire(tokens):
                    return 0.0
                wait_time = self.limiter.get_wait_time(tokens)
            
            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 0.1))
            else:
                await asyncio.sleep(0.01)


# =============================================================================
# Per-Key Rate Limiter
# =============================================================================

class PerKeyRateLimiter:
    """
    Rate limiter with separate limits per key (e.g., per user, per IP).
    """
    
    def __init__(
        self,
        limiter_factory,  # Factory function to create limiters
        cleanup_interval: float = 60.0
    ):
        self.limiter_factory = limiter_factory
        self.limiters: dict = {}
        self.last_cleanup = time.monotonic()
        self.cleanup_interval = cleanup_interval
        self._lock = threading.Lock()
    
    def _cleanup_if_needed(self) -> None:
        """Remove stale limiters periodically."""
        now = time.monotonic()
        if now - self.last_cleanup > self.cleanup_interval:
            # Simple cleanup: just clear old entries
            # In production, track last access time
            if len(self.limiters) > 10000:
                self.limiters.clear()
            self.last_cleanup = now
    
    def acquire(self, key: str, tokens: int = 1) -> bool:
        """Acquire for a specific key."""
        with self._lock:
            self._cleanup_if_needed()
            
            if key not in self.limiters:
                self.limiters[key] = self.limiter_factory()
            
            return self.limiters[key].acquire(tokens)
    
    def get_wait_time(self, key: str, tokens: int = 1) -> float:
        """Get wait time for a specific key."""
        with self._lock:
            if key not in self.limiters:
                return 0.0
            return self.limiters[key].get_wait_time(tokens)


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Rate Limiting Algorithms Demo")
    print("=" * 60)
    
    # Token Bucket Demo
    print("\n=== Token Bucket (10 tokens/sec, capacity 5) ===\n")
    bucket = TokenBucket(rate=10, capacity=5)
    
    for i in range(8):
        result = bucket.acquire()
        print(f"Request {i+1}: {'✓ Allowed' if result else '✗ Denied'}")
    
    print(f"\nWait time for next token: {bucket.get_wait_time():.3f}s")
    
    # Sliding Window Log Demo
    print("\n=== Sliding Window Log (5 requests/second) ===\n")
    window = SlidingWindowLog(limit=5, window_seconds=1.0)
    
    for i in range(7):
        result = window.acquire()
        print(f"Request {i+1}: {'✓ Allowed' if result else '✗ Denied'} (count: {window.current_count()})")
    
    # Fixed Window Demo
    print("\n=== Fixed Window (3 requests/second) ===\n")
    fixed = FixedWindowCounter(limit=3, window_seconds=1.0)
    
    for i in range(5):
        result = fixed.acquire()
        print(f"Request {i+1}: {'✓ Allowed' if result else '✗ Denied'}")
    
    print("\nWaiting for window reset...")
    time.sleep(1.1)
    
    result = fixed.acquire()
    print(f"After reset: {'✓ Allowed' if result else '✗ Denied'}")
    
    # Per-Key Demo
    print("\n=== Per-Key Rate Limiting ===\n")
    per_key = PerKeyRateLimiter(
        lambda: TokenBucket(rate=2, capacity=3)
    )
    
    for user in ["user1", "user2", "user1", "user1", "user2"]:
        result = per_key.acquire(user)
        print(f"{user}: {'✓ Allowed' if result else '✗ Denied'}")
    
    print("\n" + "=" * 60)
