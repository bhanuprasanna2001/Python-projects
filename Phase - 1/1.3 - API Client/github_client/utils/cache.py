"""Response caching with TTL and ETag support.

This module provides in-memory caching for GitHub API responses
with time-based expiration and ETag support for conditional requests.

Features:
    - TTL-based expiration
    - ETag storage for conditional If-None-Match requests
    - Auth-aware cache keys (different auth = different cache)
    - Thread-safe operations

"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached response with metadata.

    Attributes:
        data: The cached response data.
        etag: ETag value for conditional requests.
        expires_at: Unix timestamp when entry expires.
        created_at: Unix timestamp when entry was created.

    """

    data: Any
    etag: str | None
    expires_at: float
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        return time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> float:
        """Get remaining time-to-live in seconds."""
        return max(0.0, self.expires_at - time.time())


class ResponseCache:
    """In-memory cache for API responses.

    This cache stores responses with TTL-based expiration and
    supports ETag-based conditional requests.

    Attributes:
        default_ttl: Default time-to-live in seconds.

    Example:
        >>> cache = ResponseCache(default_ttl=300)
        >>> cache.set("key", data, etag="abc123")
        >>> entry = cache.get("key")
        >>> if entry:
        ...     return entry.data

    """

    __slots__ = ("_cache", "_default_ttl", "_lock")

    def __init__(self, default_ttl: int = 300) -> None:
        """Initialize the cache.

        Args:
            default_ttl: Default time-to-live in seconds.

        """
        self._default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> CacheEntry | None:
        """Get a cached entry if not expired.

        Args:
            key: The cache key.

        Returns:
            CacheEntry if found and not expired, None otherwise.

        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return None

            if entry.is_expired:
                del self._cache[key]
                logger.debug("Cache expired: %s", key[:50])
                return None

            logger.debug("Cache hit: %s", key[:50])
            return entry

    def set(
        self,
        key: str,
        data: Any,
        etag: str | None = None,
        ttl: int | None = None,
    ) -> None:
        """Store a response in the cache.

        Args:
            key: The cache key.
            data: The response data to cache.
            etag: ETag value for conditional requests.
            ttl: Time-to-live in seconds (uses default if None).

        """
        actual_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + actual_ttl

        entry = CacheEntry(
            data=data,
            etag=etag,
            expires_at=expires_at,
        )

        with self._lock:
            self._cache[key] = entry

        logger.debug("Cache set: %s (TTL: %ds)", key[:50], actual_ttl)

    def get_etag(self, key: str) -> str | None:
        """Get stored ETag for conditional request.

        This returns the ETag even for expired entries,
        allowing conditional requests to validate stale data.

        Args:
            key: The cache key.

        Returns:
            ETag string if stored, None otherwise.

        """
        with self._lock:
            entry = self._cache.get(key)
            return entry.etag if entry else None

    def refresh_ttl(self, key: str, ttl: int | None = None) -> bool:
        """Refresh the TTL of an existing entry.

        Used when a 304 Not Modified response validates the cache.

        Args:
            key: The cache key.
            ttl: New TTL in seconds (uses default if None).

        Returns:
            True if entry was refreshed, False if not found.

        """
        actual_ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            entry.expires_at = time.time() + actual_ttl
            logger.debug("Cache TTL refreshed: %s", key[:50])
            return True

    def invalidate(self, key: str) -> bool:
        """Remove a specific entry from the cache.

        Args:
            key: The cache key.

        Returns:
            True if entry was removed, False if not found.

        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug("Cache invalidated: %s", key[:50])
                return True
            return False

    def clear(self) -> int:
        """Remove all entries from the cache.

        Returns:
            Number of entries removed.

        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()

        logger.debug("Cache cleared: %d entries", count)
        return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed.

        """
        now = time.time()
        removed = 0

        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if now > entry.expires_at]
            for key in expired_keys:
                del self._cache[key]
                removed += 1

        if removed:
            logger.debug("Cleaned up %d expired entries", removed)

        return removed

    @property
    def size(self) -> int:
        """Get the number of cached entries."""
        with self._lock:
            return len(self._cache)

    def __repr__(self) -> str:
        """Return a string representation."""
        return f"ResponseCache(size={self.size}, default_ttl={self._default_ttl})"


def make_cache_key(
    method: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
    is_authenticated: bool = False,
) -> str:
    """Generate a cache key for a request.

    The key includes method, endpoint, params, and auth status
    to ensure different contexts get different cache entries.

    Args:
        method: HTTP method.
        endpoint: API endpoint path.
        params: Query parameters.
        is_authenticated: Whether request is authenticated.

    Returns:
        A unique cache key string.

    """
    # Sort params for consistent key generation
    param_str = ""
    if params:
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)

    auth_str = "auth" if is_authenticated else "anon"

    # Create a readable key with hash for long param strings
    base_key = f"{method}:{endpoint}:{auth_str}"

    if param_str:
        if len(param_str) > 50:
            # Hash long param strings
            param_hash = hashlib.md5(param_str.encode(), usedforsecurity=False).hexdigest()[:8]
            return f"{base_key}:p={param_hash}"
        return f"{base_key}:{param_str}"

    return base_key
