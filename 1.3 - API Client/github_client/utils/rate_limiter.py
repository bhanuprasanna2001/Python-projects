"""Rate limiter using GitHub's response headers.

This module provides proactive rate limiting by tracking GitHub's
rate limit headers and throttling requests before hitting limits.

GitHub Rate Limit Resources:
    - core: 5000/hour (authenticated), 60/hour (unauthenticated)

Headers Used:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Requests remaining
    - X-RateLimit-Reset: Unix timestamp when limit resets
    - X-RateLimit-Resource: Which resource (core)

"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit information for a single resource.

    Attributes:
        limit: Maximum requests allowed in the window.
        remaining: Requests remaining in current window.
        reset_at: When the rate limit resets.
        resource: The rate limit resource name.

    """

    limit: int
    remaining: int
    reset_at: datetime
    resource: str = "core"

    @property
    def reset_timestamp(self) -> float:
        """Get reset time as Unix timestamp."""
        return self.reset_at.timestamp()

    @property
    def is_exceeded(self) -> bool:
        """Check if rate limit is exceeded."""
        return self.remaining <= 0

    @property
    def utilization(self) -> float:
        """Get utilization as a fraction (0.0 to 1.0)."""
        if self.limit == 0:
            return 1.0
        return 1.0 - (self.remaining / self.limit)


@dataclass
class RateLimiter:
    """Proactive rate limiter using GitHub's response headers.

    This class tracks rate limit state from response headers and
    provides methods to check if requests should be throttled.

    Attributes:
        buffer: Fraction of limit to keep as buffer (0.0-1.0).

    Example:
        >>> limiter = RateLimiter(buffer=0.1)
        >>> limiter.update_from_headers(response_headers)
        >>> limiter.wait_if_needed("core")

    """

    buffer: float = 0.1
    _limits: dict[str, RateLimitInfo] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update_from_headers(self, headers: dict[str, str]) -> None:
        """Update rate limit info from response headers.

        Args:
            headers: HTTP response headers dictionary.

        """

        def get_header(name: str) -> str | None:
            return headers.get(name) or headers.get(name.lower())

        limit_str = get_header("X-RateLimit-Limit")
        remaining_str = get_header("X-RateLimit-Remaining")
        reset_str = get_header("X-RateLimit-Reset")
        resource = get_header("X-RateLimit-Resource") or "core"

        if not all([limit_str, remaining_str, reset_str]):
            return

        try:
            limit = int(limit_str)  # type: ignore[arg-type]
            remaining = int(remaining_str)  # type: ignore[arg-type]
            reset_at = datetime.fromtimestamp(int(reset_str))  # type: ignore[arg-type]
        except (ValueError, TypeError):
            logger.warning("Failed to parse rate limit headers")
            return

        with self._lock:
            self._limits[resource] = RateLimitInfo(
                limit=limit,
                remaining=remaining,
                reset_at=reset_at,
                resource=resource,
            )

        logger.debug(
            "Rate limit for %s: %d/%d (resets at %s)",
            resource,
            remaining,
            limit,
            reset_at.isoformat(),
        )

    def get_limit_info(self, resource: str = "core") -> RateLimitInfo | None:
        """Get rate limit info for a resource.

        Args:
            resource: The rate limit resource name.

        Returns:
            RateLimitInfo if available, None otherwise.

        """
        with self._lock:
            return self._limits.get(resource)

    def get_remaining(self, resource: str = "core") -> int | None:
        """Get remaining requests for a resource.

        Args:
            resource: The rate limit resource name.

        Returns:
            Number of remaining requests, or None if unknown.

        """
        info = self.get_limit_info(resource)
        return info.remaining if info else None

    def get_reset_time(self, resource: str = "core") -> datetime | None:
        """Get reset time for a resource.

        Args:
            resource: The rate limit resource name.

        Returns:
            Reset datetime, or None if unknown.

        """
        info = self.get_limit_info(resource)
        return info.reset_at if info else None

    def should_throttle(self, resource: str = "core") -> bool:
        """Check if requests should be throttled.

        This returns True if remaining requests are below the buffer
        threshold to prevent hitting the actual limit.

        Args:
            resource: The rate limit resource name.

        Returns:
            True if requests should be throttled.

        """
        info = self.get_limit_info(resource)
        if not info:
            return False

        # Check if we're past reset time
        if time.time() > info.reset_timestamp:
            return False

        # Check if we're below buffer threshold
        threshold = int(info.limit * self.buffer)
        return info.remaining <= threshold

    def get_wait_time(self, resource: str = "core") -> float:
        """Calculate how long to wait before next request.

        Args:
            resource: The rate limit resource name.

        Returns:
            Seconds to wait, or 0 if no wait needed.

        """
        info = self.get_limit_info(resource)
        if not info:
            return 0.0

        if not self.should_throttle(resource):
            return 0.0

        wait_time = info.reset_timestamp - time.time()
        return max(0.0, wait_time)

    def wait_if_needed(self, resource: str = "core") -> float:
        """Block until rate limit allows more requests.

        Args:
            resource: The rate limit resource name.

        Returns:
            Seconds waited (0 if no wait was needed).

        """
        wait_time = self.get_wait_time(resource)

        if wait_time > 0:
            logger.info(
                "Rate limit buffer reached for %s, waiting %.2fs",
                resource,
                wait_time,
            )
            time.sleep(wait_time)

        return wait_time

    def clear(self) -> None:
        """Clear all stored rate limit information."""
        with self._lock:
            self._limits.clear()

    def __repr__(self) -> str:
        """Return a string representation."""
        with self._lock:
            resources = list(self._limits.keys())
        return f"RateLimiter(buffer={self.buffer}, resources={resources})"
