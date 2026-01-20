"""
Async Patterns
==============
Common patterns for async programming.
"""

import asyncio
from typing import Any, Callable, TypeVar, List
from functools import wraps
import time

T = TypeVar('T')


# ============================================================
# 1. Semaphore - Rate Limiting
# ============================================================

async def limited_fetch(
    semaphore: asyncio.Semaphore, 
    url: str,
    delay: float
) -> dict:
    """Fetch with concurrency limit."""
    async with semaphore:  # Only N concurrent fetches
        print(f"  Fetching {url}...")
        await asyncio.sleep(delay)
        return {"url": url, "status": 200}


async def semaphore_demo():
    """
    Use semaphore to limit concurrent operations.
    Prevents overwhelming external services.
    """
    print("\n--- Semaphore (Rate Limiting) ---")
    
    # Limit to 3 concurrent requests
    semaphore = asyncio.Semaphore(3)
    
    urls = [f"https://api.example.com/item/{i}" for i in range(10)]
    
    start = time.perf_counter()
    
    # All 10 URLs, but only 3 at a time
    tasks = [limited_fetch(semaphore, url, 1.0) for url in urls]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.perf_counter() - start
    print(f"Fetched {len(results)} URLs in {elapsed:.2f}s")
    print("(Should be ~4s: 10 URLs / 3 concurrent = 4 batches)")


# ============================================================
# 2. Lock - Mutual Exclusion
# ============================================================

class AsyncCounter:
    """Thread-safe async counter using Lock."""
    
    def __init__(self):
        self.value = 0
        self._lock = asyncio.Lock()
    
    async def increment(self):
        """Safely increment counter."""
        async with self._lock:
            # Critical section - only one coroutine at a time
            current = self.value
            await asyncio.sleep(0.1)  # Simulate some work
            self.value = current + 1
    
    async def get(self) -> int:
        async with self._lock:
            return self.value


async def lock_demo():
    """Demonstrate Lock for mutual exclusion."""
    print("\n--- Lock (Mutual Exclusion) ---")
    
    counter = AsyncCounter()
    
    # Without lock, this would cause race conditions
    async def increment_many(n: int):
        for _ in range(n):
            await counter.increment()
    
    # Run 5 tasks, each incrementing 4 times
    await asyncio.gather(*[increment_many(4) for _ in range(5)])
    
    print(f"Final count: {await counter.get()}")
    print("(Should be 20)")


# ============================================================
# 3. Event - Signaling
# ============================================================

async def waiter(event: asyncio.Event, name: str):
    """Wait for event to be set."""
    print(f"[{name}] Waiting for signal...")
    await event.wait()
    print(f"[{name}] Got signal, proceeding!")


async def setter(event: asyncio.Event):
    """Set the event after delay."""
    print("[Setter] Will signal in 2 seconds...")
    await asyncio.sleep(2)
    print("[Setter] Signaling!")
    event.set()


async def event_demo():
    """Demonstrate Event for coordination."""
    print("\n--- Event (Signaling) ---")
    
    event = asyncio.Event()
    
    # Multiple waiters, one setter
    await asyncio.gather(
        waiter(event, "W1"),
        waiter(event, "W2"),
        waiter(event, "W3"),
        setter(event)
    )


# ============================================================
# 4. Queue - Producer/Consumer
# ============================================================

async def producer(queue: asyncio.Queue, items: List[Any]):
    """Produce items to queue."""
    for item in items:
        await asyncio.sleep(0.5)  # Simulate production time
        await queue.put(item)
        print(f"[Producer] Put: {item}")
    
    # Signal completion
    await queue.put(None)


async def consumer(queue: asyncio.Queue, name: str):
    """Consume items from queue."""
    while True:
        item = await queue.get()
        
        if item is None:
            # Pass along the termination signal
            await queue.put(None)
            break
        
        print(f"[{name}] Processing: {item}")
        await asyncio.sleep(0.3)  # Simulate processing time
        
        queue.task_done()
    
    print(f"[{name}] Done!")


async def queue_demo():
    """Demonstrate Queue for producer/consumer."""
    print("\n--- Queue (Producer/Consumer) ---")
    
    queue = asyncio.Queue(maxsize=5)  # Bounded queue
    
    items = ["task1", "task2", "task3", "task4", "task5"]
    
    await asyncio.gather(
        producer(queue, items),
        consumer(queue, "Consumer1"),
        consumer(queue, "Consumer2")
    )


# ============================================================
# 5. Retry Pattern
# ============================================================

class RetryError(Exception):
    """Raised when all retries exhausted."""
    pass


async def retry_async(
    coro_func: Callable,
    *args,
    max_retries: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = True,
    **kwargs
) -> Any:
    """
    Retry an async operation with backoff.
    
    Args:
        coro_func: Async function to retry
        max_retries: Maximum retry attempts
        delay: Initial delay between retries
        exponential_backoff: Double delay each retry
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt if exponential_backoff else 1)
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    
    raise RetryError(f"All {max_retries} retries failed") from last_exception


async def flaky_operation(fail_count: int = 2) -> str:
    """Operation that fails first N times."""
    flaky_operation.attempts = getattr(flaky_operation, 'attempts', 0) + 1
    
    if flaky_operation.attempts <= fail_count:
        raise ConnectionError(f"Attempt {flaky_operation.attempts} failed")
    
    return f"Success on attempt {flaky_operation.attempts}"


async def retry_demo():
    """Demonstrate retry pattern."""
    print("\n--- Retry Pattern ---")
    
    flaky_operation.attempts = 0  # Reset
    
    try:
        result = await retry_async(
            flaky_operation,
            fail_count=2,
            max_retries=5,
            delay=0.5
        )
        print(f"Final result: {result}")
    except RetryError as e:
        print(f"Failed: {e}")


# ============================================================
# 6. Circuit Breaker Pattern
# ============================================================

class CircuitBreaker:
    """
    Circuit breaker for failing services.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Service failing, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
    
    async def call(self, coro_func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        
        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == self.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                print("[CB] Transitioning to HALF_OPEN")
                self.state = self.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await coro_func(*args, **kwargs)
            
            # Success - reset failures
            if self.state == self.HALF_OPEN:
                print("[CB] Service recovered, closing circuit")
                self.state = self.CLOSED
            self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                print(f"[CB] Threshold reached, opening circuit")
                self.state = self.OPEN
            
            raise


async def circuit_breaker_demo():
    """Demonstrate circuit breaker pattern."""
    print("\n--- Circuit Breaker ---")
    
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    
    async def unreliable_service():
        import random
        if random.random() < 0.7:  # 70% failure rate
            raise ConnectionError("Service unavailable")
        return "Success"
    
    for i in range(10):
        try:
            result = await cb.call(unreliable_service)
            print(f"Request {i+1}: {result}")
        except Exception as e:
            print(f"Request {i+1}: Failed - {e}")
        
        await asyncio.sleep(0.5)


# ============================================================
# 7. Async Context Manager Decorator
# ============================================================

def async_timed(func):
    """Decorator to time async functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            print(f"[TIMER] {func.__name__} took {elapsed:.3f}s")
    return wrapper


@async_timed
async def timed_operation():
    """A timed async operation."""
    await asyncio.sleep(1.5)
    return "Done"


async def decorator_demo():
    """Demonstrate async decorator."""
    print("\n--- Async Timed Decorator ---")
    await timed_operation()


# ============================================================
# Demo Runner
# ============================================================

async def run_patterns_demo():
    """Run all pattern demos."""
    print("=" * 50)
    print("Async Patterns Demo")
    print("=" * 50)
    
    await semaphore_demo()
    await lock_demo()
    await event_demo()
    await queue_demo()
    await retry_demo()
    await circuit_breaker_demo()
    await decorator_demo()


if __name__ == "__main__":
    asyncio.run(run_patterns_demo())
