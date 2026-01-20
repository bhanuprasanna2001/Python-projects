"""
Async Python Basics
===================
Fundamental concepts of async/await.
"""

import asyncio
import time


# ============================================================
# 1. Basic Coroutine
# ============================================================

async def say_hello(name: str) -> str:
    """
    A simple coroutine function.
    
    - 'async def' defines a coroutine
    - Returns a coroutine object when called (not the result!)
    - Must be awaited to get the result
    """
    return f"Hello, {name}!"


async def say_hello_delayed(name: str, delay: float) -> str:
    """
    Coroutine with async sleep.
    
    - asyncio.sleep() is non-blocking
    - Allows other coroutines to run during sleep
    """
    await asyncio.sleep(delay)  # Yields control to event loop
    return f"Hello, {name}! (after {delay}s)"


# ============================================================
# 2. await Keyword
# ============================================================

async def demo_await():
    """
    Demonstrates the 'await' keyword.
    
    - 'await' pauses coroutine execution
    - Control returns to event loop
    - Resumes when awaited operation completes
    """
    print("Starting...")
    
    # await a coroutine
    result = await say_hello("World")
    print(result)
    
    # await with delay
    result = await say_hello_delayed("Async", 1.0)
    print(result)
    
    print("Done!")


# ============================================================
# 3. Sequential vs Concurrent Execution
# ============================================================

async def fetch_data(item_id: int, delay: float) -> dict:
    """Simulate fetching data with network delay."""
    print(f"  Fetching item {item_id}...")
    await asyncio.sleep(delay)
    print(f"  Fetched item {item_id}")
    return {"id": item_id, "data": f"Data for {item_id}"}


async def sequential_example():
    """
    Sequential execution - one after another.
    Total time: sum of all delays.
    """
    print("\n--- Sequential Execution ---")
    start = time.perf_counter()
    
    # Each await completes before next starts
    result1 = await fetch_data(1, 1.0)
    result2 = await fetch_data(2, 1.0)
    result3 = await fetch_data(3, 1.0)
    
    elapsed = time.perf_counter() - start
    print(f"Sequential took: {elapsed:.2f}s")
    return [result1, result2, result3]


async def concurrent_example():
    """
    Concurrent execution - all at once.
    Total time: max of all delays (not sum!).
    """
    print("\n--- Concurrent Execution ---")
    start = time.perf_counter()
    
    # Create coroutines (not started yet)
    coro1 = fetch_data(1, 1.0)
    coro2 = fetch_data(2, 1.0)
    coro3 = fetch_data(3, 1.0)
    
    # Run all concurrently with gather
    results = await asyncio.gather(coro1, coro2, coro3)
    
    elapsed = time.perf_counter() - start
    print(f"Concurrent took: {elapsed:.2f}s")
    return results


# ============================================================
# 4. Running Coroutines
# ============================================================

def demo_running_coroutines():
    """Different ways to run coroutines."""
    
    # Method 1: asyncio.run() - Most common
    # Creates event loop, runs coroutine, closes loop
    result = asyncio.run(say_hello("Method 1"))
    print(result)
    
    # Method 2: Get existing event loop (in async context)
    # loop = asyncio.get_event_loop()
    # result = loop.run_until_complete(say_hello("Method 2"))
    
    # Method 3: Already in async context (just await)
    # result = await say_hello("Method 3")


# ============================================================
# 5. Common Mistakes
# ============================================================

async def common_mistakes():
    """Demonstrates common async mistakes."""
    
    # MISTAKE 1: Forgetting to await
    # result = say_hello("World")  # Returns coroutine, not result!
    # Correct:
    result = await say_hello("World")
    
    # MISTAKE 2: Using time.sleep instead of asyncio.sleep
    # time.sleep(1)  # BLOCKS the event loop!
    # Correct:
    await asyncio.sleep(1)
    
    # MISTAKE 3: Sequential when could be concurrent
    # Slow:
    # r1 = await fetch_data(1, 1.0)
    # r2 = await fetch_data(2, 1.0)
    # Fast:
    r1, r2 = await asyncio.gather(
        fetch_data(1, 1.0),
        fetch_data(2, 1.0)
    )
    
    # MISTAKE 4: Blocking I/O in async code
    # with open('file.txt') as f:  # Blocking!
    #     data = f.read()
    # Correct: Use aiofiles
    # async with aiofiles.open('file.txt') as f:
    #     data = await f.read()
    
    return result


# ============================================================
# 6. Return Values
# ============================================================

async def multiple_returns():
    """Working with return values from coroutines."""
    
    # Single coroutine
    single = await fetch_data(1, 0.5)
    print(f"Single: {single}")
    
    # Multiple with gather (returns list)
    results = await asyncio.gather(
        fetch_data(1, 0.5),
        fetch_data(2, 0.5),
        fetch_data(3, 0.5)
    )
    print(f"Multiple: {results}")
    
    # Unpacking gather results
    r1, r2, r3 = await asyncio.gather(
        fetch_data(1, 0.5),
        fetch_data(2, 0.5),
        fetch_data(3, 0.5)
    )
    print(f"Unpacked: {r1}, {r2}, {r3}")


# ============================================================
# Demo Runner
# ============================================================

async def run_basics_demo():
    """Run all basic demos."""
    print("=" * 50)
    print("Async Python Basics")
    print("=" * 50)
    
    # Basic await
    await demo_await()
    
    # Sequential vs Concurrent
    await sequential_example()
    await concurrent_example()
    
    # Return values
    print("\n--- Return Values ---")
    await multiple_returns()


if __name__ == "__main__":
    asyncio.run(run_basics_demo())
