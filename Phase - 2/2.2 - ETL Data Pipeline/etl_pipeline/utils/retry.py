"""
Retry utilities with exponential backoff.

Provides decorators and context managers for retrying failed operations.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from etl_pipeline.utils.logging import get_logger

logger = get_logger("retry")

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including initial)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Multiplier for exponential backoff
        jitter: Whether to add random jitter to delays
        retry_on: Tuple of exception types to retry on
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: tuple[type[Exception], ...] = field(default_factory=lambda: (Exception,))

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Uses exponential backoff with optional jitter.
        """
        delay = min(
            self.base_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay,
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


def with_retry(
    config: RetryConfig | None = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to retry a synchronous function on failure.

    Args:
        config: RetryConfig instance (overrides other params if provided)
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        retry_on: Exception types to retry on

    Example:
        @with_retry(max_attempts=3, retry_on=(ConnectionError,))
        def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            retry_on=retry_on,
        )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s...",
                            extra={
                                "attempt": attempt,
                                "max_attempts": config.max_attempts,
                                "delay": delay,
                                "error": str(e),
                            },
                        )
                        import time

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed",
                            extra={"error": str(e)},
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


def with_async_retry(
    config: RetryConfig | None = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator to retry an async function on failure.

    Args:
        config: RetryConfig instance (overrides other params if provided)
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        retry_on: Exception types to retry on

    Example:
        @with_async_retry(max_attempts=3, retry_on=(httpx.HTTPError,))
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            retry_on=retry_on,
        )

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s...",
                            extra={
                                "attempt": attempt,
                                "max_attempts": config.max_attempts,
                                "delay": delay,
                                "error": str(e),
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed",
                            extra={"error": str(e)},
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


class RetryContext:
    """
    Context manager for retry logic.

    Useful when you need more control over the retry loop.

    Example:
        async with RetryContext(max_attempts=3) as retry:
            while retry.should_continue:
                try:
                    result = await fetch_data()
                    break
                except ConnectionError as e:
                    await retry.handle_error(e)
    """

    def __init__(self, config: RetryConfig | None = None, **kwargs: Any) -> None:
        self.config = config or RetryConfig(**kwargs)
        self.attempt = 0
        self.last_error: Exception | None = None

    @property
    def should_continue(self) -> bool:
        """Check if more attempts are allowed."""
        return self.attempt < self.config.max_attempts

    async def handle_error(self, error: Exception) -> None:
        """Handle an error and wait before next attempt."""
        self.last_error = error
        self.attempt += 1

        if self.should_continue:
            delay = self.config.get_delay(self.attempt)
            logger.warning(
                f"Attempt {self.attempt}/{self.config.max_attempts} failed: {error}. "
                f"Retrying in {delay:.2f}s...",
            )
            await asyncio.sleep(delay)
        else:
            raise error

    async def __aenter__(self) -> RetryContext:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass
