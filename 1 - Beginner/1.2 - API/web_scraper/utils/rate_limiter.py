"""Domain-aware rate limiter."""

from __future__ import annotations

import time
from collections import defaultdict
from urllib.parse import urlparse


class RateLimiter:
    """Simple per-domain rate limiter using fixed delay.

    Thread-safe for single-threaded async usage.
    For true thread safety, add threading.Lock per domain.
    """

    def __init__(self, default_delay: float = 1.0) -> None:
        """Initialize rate limiter.

        Args:
            default_delay: Seconds between requests to same domain
        """
        self._default_delay = default_delay
        self._last_request: dict[str, float] = defaultdict(float)
        self._domain_delays: dict[str, float] = {}

    def wait(self, url: str) -> None:
        """Block until it's safe to request this URL's domain."""
        domain = urlparse(url).netloc
        delay = self._domain_delays.get(domain, self._default_delay)

        elapsed = time.monotonic() - self._last_request[domain]
        if elapsed < delay:
            time.sleep(delay - elapsed)

        self._last_request[domain] = time.monotonic()
