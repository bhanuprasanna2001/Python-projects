"""Retry logic with exponential backoff for transient failures.

This module provides a retry decorator that handles transient failures
gracefully with configurable backoff and jitter.

Retry Conditions:
    - 429 Too Many Requests (respects Retry-After header)
    - 500, 502, 503, 504 Server Errors
    - Network errors classified as retryable

Non-Retryable:
    - 400, 401, 403, 404, 422 (client errors)
    - DNS resolution failures

"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from github_client.exceptions import GitHubError, NetworkError, RateLimitError, ServerError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Status codes that warrant a retry
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error should trigger a retry.

    Args:
        error: The exception to check.

    Returns:
        True if the error is transient and retryable.

    """
    if isinstance(error, RateLimitError):
        return True

    if isinstance(error, ServerError):
        return error.status_code in RETRYABLE_STATUS_CODES

    if isinstance(error, NetworkError):
        return error.is_retryable

    return False


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate delay for exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed).
        base_delay: Initial delay in seconds.
        factor: Exponential factor.
        max_delay: Maximum delay cap.
        jitter: Add randomness to prevent thundering herd.

    Returns:
        Delay in seconds before next retry.

    """
    delay = min(base_delay * (factor**attempt), max_delay)

    if jitter:
        # Add ±25% jitter
        delay = delay * (0.75 + random.random() * 0.5)  # nosec B311

    return delay


def get_retry_after(error: RateLimitError) -> float | None:
    """Extract retry delay from RateLimitError.

    Args:
        error: The rate limit error.

    Returns:
        Seconds to wait, or None if not specified.

    """
    if error.retry_after:
        return float(error.retry_after)

    if error.reset_at:
        wait_time = error.reset_at.timestamp() - time.time()
        return max(0.0, wait_time)

    return None


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that retries a function on transient failures.

    Args:
        max_attempts: Maximum number of attempts (including first try).
        base_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for exponential backoff.
        max_delay: Maximum delay between retries.

    Returns:
        Decorated function with retry logic.

    Example:
        >>> @retry(max_attempts=3, base_delay=1.0)
        ... def make_request():
        ...     return http_client.get("/endpoint")

    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Exception | None = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (RateLimitError, ServerError, NetworkError, GitHubError) as e:
                    last_error = e

                    # Check if we should retry
                    if not is_retryable_error(e):
                        raise

                    # Check if we have attempts left
                    if attempt >= max_attempts - 1:
                        logger.warning(
                            "Max retries (%d) exhausted for %s",
                            max_attempts,
                            func.__name__,
                        )
                        raise

                    # Calculate delay
                    if isinstance(e, RateLimitError):
                        retry_after = get_retry_after(e)
                        delay = (
                            retry_after
                            if retry_after
                            else calculate_backoff(attempt, base_delay, backoff_factor, max_delay)
                        )
                    else:
                        delay = calculate_backoff(attempt, base_delay, backoff_factor, max_delay)

                    logger.info(
                        "Retry %d/%d for %s after %.2fs: %s",
                        attempt + 1,
                        max_attempts - 1,
                        func.__name__,
                        delay,
                        str(e),
                    )

                    time.sleep(delay)

            # Should never reach here, but satisfy type checker
            if last_error:
                raise last_error
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


class RetryConfig:
    """Configuration for retry behavior.

    This class encapsulates retry settings for easy passing around.

    """

    __slots__ = ("backoff_factor", "base_delay", "max_attempts", "max_delay")

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
    ) -> None:
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts.
            base_delay: Initial delay in seconds.
            backoff_factor: Exponential backoff multiplier.
            max_delay: Maximum delay cap.

        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    @classmethod
    def from_client_config(cls, config: Any) -> RetryConfig:
        """Create RetryConfig from ClientConfig.

        Args:
            config: ClientConfig instance.

        Returns:
            RetryConfig with values from ClientConfig.

        """
        return cls(
            max_attempts=config.max_retries,
            backoff_factor=config.retry_backoff_factor,
        )
