"""
Async Tasks
===========
Task creation, management, and control.
"""

import asyncio
from typing import List, Any


# ============================================================
# 1. Creating Tasks
# ============================================================

async def worker(name: str, duration: float) -> str:
    """Simple worker coroutine."""
    print(f"[{name}] Starting...")
    await asyncio.sleep(duration)
    print(f"[{name}] Finished!")
    return f"{name} completed"


async def create_tasks_demo():
    """
    Different ways to create and manage tasks.
    
    Task = A scheduled coroutine that runs in the background
    """
    print("\n--- Creating Tasks ---")
    
    # Method 1: asyncio.create_task() - Recommended
    task1 = asyncio.create_task(worker("Task1", 1.0))
    task2 = asyncio.create_task(worker("Task2", 1.5))
    
    # Tasks start immediately after creation!
    print("Tasks created and running...")
    
    # Wait for tasks to complete
    result1 = await task1
    result2 = await task2
    print(f"Results: {result1}, {result2}")
    
    # Method 2: asyncio.ensure_future() - Also works
    future = asyncio.ensure_future(worker("Future", 0.5))
    await future


# ============================================================
# 2. Task Properties
# ============================================================

async def task_properties_demo():
    """Examine task properties and state."""
    print("\n--- Task Properties ---")
    
    task = asyncio.create_task(worker("PropertyDemo", 1.0), name="my-task")
    
    # Task name
    print(f"Task name: {task.get_name()}")
    
    # Check state
    print(f"Done: {task.done()}")
    print(f"Cancelled: {task.cancelled()}")
    
    await asyncio.sleep(0.5)  # Let it run a bit
    print(f"After 0.5s - Done: {task.done()}")
    
    await task  # Wait for completion
    print(f"After await - Done: {task.done()}")
    
    # Get result (only after done)
    print(f"Result: {task.result()}")


# ============================================================
# 3. Task Cancellation
# ============================================================

async def long_running_task(name: str):
    """A task that can be cancelled."""
    try:
        print(f"[{name}] Starting long task...")
        for i in range(10):
            print(f"[{name}] Step {i+1}/10")
            await asyncio.sleep(1)
        return f"{name} completed all steps"
    except asyncio.CancelledError:
        print(f"[{name}] Was cancelled!")
        # Perform cleanup here
        raise  # Re-raise to properly cancel


async def cancellation_demo():
    """Demonstrate task cancellation."""
    print("\n--- Task Cancellation ---")
    
    task = asyncio.create_task(long_running_task("CancelDemo"))
    
    # Let it run for a bit
    await asyncio.sleep(2.5)
    
    # Cancel the task
    print("Requesting cancellation...")
    task.cancel()
    
    # Wait for cancellation to complete
    try:
        await task
    except asyncio.CancelledError:
        print("Task was cancelled successfully")
    
    print(f"Cancelled: {task.cancelled()}")


# ============================================================
# 4. Timeouts
# ============================================================

async def slow_operation(duration: float) -> str:
    """Operation that might be slow."""
    await asyncio.sleep(duration)
    return "Operation completed"


async def timeout_demo():
    """Demonstrate timeout handling."""
    print("\n--- Timeouts ---")
    
    # Method 1: asyncio.wait_for()
    print("Using wait_for with 2s timeout on 3s operation:")
    try:
        result = await asyncio.wait_for(
            slow_operation(3.0),
            timeout=2.0
        )
        print(f"Result: {result}")
    except asyncio.TimeoutError:
        print("Operation timed out!")
    
    # Method 2: asyncio.timeout() context manager (Python 3.11+)
    print("\nUsing timeout context manager:")
    try:
        async with asyncio.timeout(1.0):
            await slow_operation(0.5)  # Will complete
            print("First operation completed")
            
            await slow_operation(2.0)  # Will timeout
            print("Second operation completed")
    except asyncio.TimeoutError:
        print("Context timed out!")
    
    # Method 3: Wait with timeout (returns done/pending)
    print("\nUsing wait with timeout:")
    tasks = [
        asyncio.create_task(slow_operation(0.5)),
        asyncio.create_task(slow_operation(3.0)),
    ]
    
    done, pending = await asyncio.wait(tasks, timeout=1.0)
    print(f"Completed: {len(done)}, Pending: {len(pending)}")
    
    # Cancel pending tasks
    for task in pending:
        task.cancel()


# ============================================================
# 5. Task Groups (Python 3.11+)
# ============================================================

async def task_groups_demo():
    """
    TaskGroup provides structured concurrency.
    All tasks must complete (or be cancelled) before exiting.
    """
    print("\n--- Task Groups (Python 3.11+) ---")
    
    results = []
    
    try:
        async with asyncio.TaskGroup() as tg:
            # Tasks created in group are awaited automatically
            task1 = tg.create_task(worker("TG-1", 1.0))
            task2 = tg.create_task(worker("TG-2", 0.5))
            task3 = tg.create_task(worker("TG-3", 1.5))
    except* Exception as e:
        # ExceptionGroup handling (Python 3.11+)
        print(f"Some tasks failed: {e}")
    
    # All tasks completed here
    print("All tasks in group completed!")


# ============================================================
# 6. Gathering Multiple Tasks
# ============================================================

async def gather_demo():
    """Different ways to run multiple tasks."""
    print("\n--- Gathering Tasks ---")
    
    # asyncio.gather - Most common
    print("Using gather:")
    results = await asyncio.gather(
        worker("G1", 1.0),
        worker("G2", 0.5),
        worker("G3", 1.5),
        return_exceptions=True  # Don't stop on first exception
    )
    print(f"Results: {results}")
    
    # asyncio.wait - More control
    print("\nUsing wait:")
    tasks = [
        asyncio.create_task(worker("W1", 1.0)),
        asyncio.create_task(worker("W2", 0.5)),
        asyncio.create_task(worker("W3", 1.5)),
    ]
    
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED  # or ALL_COMPLETED, FIRST_EXCEPTION
    )
    print(f"First completed: {[t.result() for t in done]}")
    
    # Wait for rest
    if pending:
        await asyncio.wait(pending)


# ============================================================
# 7. as_completed - Process Results as They Finish
# ============================================================

async def fetch_url(url: str, delay: float) -> dict:
    """Simulate fetching a URL."""
    await asyncio.sleep(delay)
    return {"url": url, "status": 200}


async def as_completed_demo():
    """Process results as each task completes."""
    print("\n--- as_completed ---")
    
    # Tasks with different durations
    tasks = [
        fetch_url("https://api1.com", 2.0),
        fetch_url("https://api2.com", 0.5),  # Fastest
        fetch_url("https://api3.com", 1.0),
    ]
    
    # Process in completion order (not creation order)
    for coro in asyncio.as_completed(tasks):
        result = await coro
        print(f"Received: {result}")


# ============================================================
# Demo Runner
# ============================================================

async def run_tasks_demo():
    """Run all task demos."""
    print("=" * 50)
    print("Async Tasks Demo")
    print("=" * 50)
    
    await create_tasks_demo()
    await task_properties_demo()
    await cancellation_demo()
    await timeout_demo()
    
    # Python 3.11+ only
    try:
        await task_groups_demo()
    except AttributeError:
        print("\nTaskGroup requires Python 3.11+")
    
    await gather_demo()
    await as_completed_demo()


if __name__ == "__main__":
    asyncio.run(run_tasks_demo())
