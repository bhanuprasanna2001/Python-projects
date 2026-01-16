"""Retry decorator with exponential backoff."""

from __future__ import annotations

import time
import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)

def retry(
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    exceptions: tuple[type[Exception], ...] = (Exception, ),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoof_factor: Exponential backoff multiplier
        exceptions: Tuple of exceptions to catch and retry
        
    Return:
        Decorated function with retry logic
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attemps: {e}"
                        )
                        raise
                    
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"{func.__name__} attempt {attempt} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    
            return func(*args, **kwargs)
        return wrapper
    return decorator