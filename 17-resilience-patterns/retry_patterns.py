"""
Retry Patterns with Backoff
===========================
Various retry strategies and backoff algorithms.
"""

import time
import random
import functools
import asyncio
from typing import Callable, Type, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Backoff Strategies
# =============================================================================

class BackoffStrategy(Enum):
    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    DECORRELATED_JITTER = "decorrelated_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    multiplier: float = 2.0
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable] = None


class BackoffCalculator:
    """Calculate delay based on backoff strategy."""
    
    @staticmethod
    def constant(attempt: int, config: RetryConfig) -> float:
        """Constant delay between retries."""
        return config.initial_delay
    
    @staticmethod
    def linear(attempt: int, config: RetryConfig) -> float:
        """Linear increase: delay = initial * attempt."""
        delay = config.initial_delay * attempt
        return min(delay, config.max_delay)
    
    @staticmethod
    def exponential(attempt: int, config: RetryConfig) -> float:
        """Exponential backoff: delay = initial * multiplier^(attempt-1)."""
        delay = config.initial_delay * (config.multiplier ** (attempt - 1))
        return min(delay, config.max_delay)
    
    @staticmethod
    def exponential_jitter(attempt: int, config: RetryConfig) -> float:
        """Exponential backoff with full jitter."""
        base_delay = BackoffCalculator.exponential(attempt, config)
        # Full jitter: random between 0 and calculated delay
        return random.uniform(0, base_delay)
    
    @staticmethod
    def decorrelated_jitter(
        attempt: int,
        config: RetryConfig,
        previous_delay: float
    ) -> float:
        """
        Decorrelated jitter (AWS recommendation).
        delay = random_between(initial, previous_delay * 3)
        """
        if attempt == 1:
            return config.initial_delay
        
        delay = random.uniform(config.initial_delay, previous_delay * 3)
        return min(delay, config.max_delay)
    
    @staticmethod
    def get_delay(
        attempt: int,
        config: RetryConfig,
        previous_delay: float = 0
    ) -> float:
        """Get delay based on configured strategy."""
        strategy = config.backoff_strategy
        
        if strategy == BackoffStrategy.CONSTANT:
            return BackoffCalculator.constant(attempt, config)
        elif strategy == BackoffStrategy.LINEAR:
            return BackoffCalculator.linear(attempt, config)
        elif strategy == BackoffStrategy.EXPONENTIAL:
            return BackoffCalculator.exponential(attempt, config)
        elif strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            return BackoffCalculator.exponential_jitter(attempt, config)
        elif strategy == BackoffStrategy.DECORRELATED_JITTER:
            return BackoffCalculator.decorrelated_jitter(attempt, config, previous_delay)
        else:
            return config.initial_delay


# =============================================================================
# Retry Decorator (Synchronous)
# =============================================================================

def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER,
    multiplier: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator for retrying functions with configurable backoff.
    
    Usage:
        @retry(max_retries=3, backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER)
        def unreliable_function():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        multiplier=multiplier,
        retryable_exceptions=retryable_exceptions,
        on_retry=on_retry,
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            previous_delay = config.initial_delay
            
            for attempt in range(1, config.max_retries + 2):  # +1 for initial try
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt > config.max_retries:
                        logger.error(f"Max retries ({config.max_retries}) exceeded")
                        raise
                    
                    delay = BackoffCalculator.get_delay(attempt, config, previous_delay)
                    previous_delay = delay
                    
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if config.on_retry:
                        config.on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# =============================================================================
# Async Retry Decorator
# =============================================================================

def async_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER,
    multiplier: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Async decorator for retrying coroutines with configurable backoff.
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        multiplier=multiplier,
        retryable_exceptions=retryable_exceptions,
        on_retry=on_retry,
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            previous_delay = config.initial_delay
            
            for attempt in range(1, config.max_retries + 2):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt > config.max_retries:
                        logger.error(f"Max retries ({config.max_retries}) exceeded")
                        raise
                    
                    delay = BackoffCalculator.get_delay(attempt, config, previous_delay)
                    previous_delay = delay
                    
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if config.on_retry:
                        config.on_retry(e, attempt)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# =============================================================================
# Retry Context Manager
# =============================================================================

class RetryContext:
    """
    Context manager for manual retry control.
    
    Usage:
        with RetryContext(max_retries=3) as ctx:
            for attempt in ctx:
                try:
                    result = do_something()
                    break
                except Exception as e:
                    ctx.handle_exception(e)
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.config = RetryConfig(
            max_retries=max_retries,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_strategy=backoff_strategy,
            retryable_exceptions=retryable_exceptions,
        )
        self.attempt = 0
        self.last_exception = None
        self.previous_delay = initial_delay
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def __iter__(self):
        return self
    
    def __next__(self) -> int:
        self.attempt += 1
        if self.attempt > self.config.max_retries + 1:
            if self.last_exception:
                raise self.last_exception
            raise StopIteration
        return self.attempt
    
    def handle_exception(self, exception: Exception) -> None:
        """Handle an exception during retry."""
        if not isinstance(exception, self.config.retryable_exceptions):
            raise exception
        
        self.last_exception = exception
        
        if self.attempt > self.config.max_retries:
            raise exception
        
        delay = BackoffCalculator.get_delay(
            self.attempt, self.config, self.previous_delay
        )
        self.previous_delay = delay
        
        logger.warning(
            f"Attempt {self.attempt} failed: {exception}. "
            f"Retrying in {delay:.2f}s..."
        )
        
        time.sleep(delay)


# =============================================================================
# Retry with Tenacity (Production-ready library)
# =============================================================================

def demonstrate_tenacity():
    """Examples using the tenacity library."""
    try:
        from tenacity import (
            retry as tenacity_retry,
            stop_after_attempt,
            stop_after_delay,
            wait_fixed,
            wait_random,
            wait_exponential,
            wait_random_exponential,
            retry_if_exception_type,
            retry_if_result,
            before_sleep_log,
            after_log,
        )
        
        # Example 1: Simple retry with exponential backoff
        @tenacity_retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
        )
        def example1():
            print("Trying...")
            raise ValueError("Always fails")
        
        # Example 2: Retry with jitter
        @tenacity_retry(
            stop=stop_after_attempt(3),
            wait=wait_random_exponential(multiplier=1, max=60),
        )
        def example2():
            pass
        
        # Example 3: Retry specific exceptions
        @tenacity_retry(
            retry=retry_if_exception_type(ConnectionError),
            stop=stop_after_attempt(5),
            wait=wait_fixed(2),
        )
        def example3():
            pass
        
        # Example 4: Retry based on return value
        @tenacity_retry(
            retry=retry_if_result(lambda x: x is None),
            stop=stop_after_attempt(3),
        )
        def example4():
            return None
        
        # Example 5: With logging
        @tenacity_retry(
            stop=stop_after_attempt(3),
            wait=wait_fixed(1),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )
        def example5():
            pass
        
        print("Tenacity examples defined successfully")
        
    except ImportError:
        print("Install tenacity: pip install tenacity")


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Retry Patterns Demo")
    print("=" * 60)
    
    # Simulate unreliable service
    call_count = 0
    
    @retry(
        max_retries=3,
        initial_delay=0.5,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    )
    def unreliable_service():
        global call_count
        call_count += 1
        
        if call_count < 3:
            raise ConnectionError(f"Connection failed (attempt {call_count})")
        
        return f"Success on attempt {call_count}"
    
    print("\n=== Retry with Exponential Backoff + Jitter ===\n")
    
    try:
        result = unreliable_service()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Final failure: {e}")
    
    # Backoff comparison
    print("\n=== Backoff Strategy Comparison ===\n")
    
    strategies = [
        BackoffStrategy.CONSTANT,
        BackoffStrategy.LINEAR,
        BackoffStrategy.EXPONENTIAL,
        BackoffStrategy.EXPONENTIAL_JITTER,
    ]
    
    for strategy in strategies:
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=60.0,
            backoff_strategy=strategy,
            multiplier=2.0,
        )
        
        delays = [
            BackoffCalculator.get_delay(i, config, config.initial_delay)
            for i in range(1, 6)
        ]
        
        print(f"{strategy.value:25} -> {[f'{d:.2f}' for d in delays]}")
    
    # Context manager
    print("\n=== Retry Context Manager ===\n")
    
    with RetryContext(max_retries=2, initial_delay=0.3) as ctx:
        for attempt in ctx:
            try:
                if attempt < 3:
                    raise ValueError(f"Failed on attempt {attempt}")
                print(f"Success on attempt {attempt}")
                break
            except ValueError as e:
                ctx.handle_exception(e)
    
    # Tenacity
    print("\n=== Tenacity Library ===\n")
    demonstrate_tenacity()
    
    print("\n" + "=" * 60)
