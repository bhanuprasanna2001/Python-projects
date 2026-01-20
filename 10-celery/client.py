"""
Celery Task Client Examples
===========================
Demonstrates various ways to call and monitor Celery tasks.
"""

from celery_app import app
from tasks.basic import (
    add, multiply, debug_task, long_task_with_progress,
    high_priority_task,
)
from tasks.workflows import (
    run_sequential_pipeline, run_parallel_fetch, run_chord_workflow,
    fetch_data, transform_data, validate_data, save_data,
)
from tasks.advanced import (
    task_with_retry, task_with_exponential_backoff,
    send_notification, heavy_computation,
)
from celery import chain, group, chord
import time


# =============================================================================
# Basic Task Invocation
# =============================================================================

def basic_examples():
    """Basic task invocation patterns."""
    print("\n=== Basic Task Invocation ===\n")
    
    # 1. Using delay() - shortcut for apply_async()
    result = add.delay(4, 4)
    print(f"Task ID: {result.id}")
    print(f"Result: {result.get(timeout=10)}")  # Wait for result
    
    # 2. Using apply_async() - more control
    result = add.apply_async(
        args=(4, 4),
        countdown=5,  # Execute after 5 seconds
    )
    print(f"Countdown task ID: {result.id}")
    
    # 3. Using signature (s) - create task signature
    sig = add.s(2, 2)
    result = sig.delay()
    print(f"Signature result: {result.get()}")
    
    # 4. Partial signature
    partial = add.s(10)  # Only first arg
    result = partial.delay(5)  # Provide second arg
    print(f"Partial result: {result.get()}")


# =============================================================================
# Checking Task Status
# =============================================================================

def check_task_status():
    """Monitor task status and results."""
    print("\n=== Task Status Monitoring ===\n")
    
    # Start a task
    result = add.delay(2, 3)
    
    # Check status
    print(f"Task ID: {result.id}")
    print(f"Status: {result.status}")
    print(f"Ready: {result.ready()}")
    print(f"Successful: {result.successful()}")
    print(f"Failed: {result.failed()}")
    
    # Wait for result
    final_result = result.get(timeout=10)
    print(f"Result: {final_result}")
    
    # After completion
    print(f"Status after: {result.status}")
    print(f"Ready after: {result.ready()}")


def monitor_progress():
    """Monitor long-running task progress."""
    print("\n=== Progress Monitoring ===\n")
    
    result = long_task_with_progress.delay(20)
    
    while not result.ready():
        if result.state == "PROGRESS":
            info = result.info
            print(f"Progress: {info['percent']}% ({info['current']}/{info['total']})")
        elif result.state == "PENDING":
            print("Task pending...")
        time.sleep(0.5)
    
    print(f"Final result: {result.get()}")


# =============================================================================
# Workflow Examples
# =============================================================================

def chain_example():
    """Execute tasks in sequence."""
    print("\n=== Chain Example ===\n")
    
    # Result of each task is passed to the next
    workflow = chain(
        add.s(2, 2),      # 4
        multiply.s(3),     # 12
        multiply.s(2),     # 24
    )
    
    result = workflow.apply_async()
    print(f"Chain result: {result.get()}")


def group_example():
    """Execute tasks in parallel."""
    print("\n=== Group Example ===\n")
    
    # All tasks run in parallel
    workflow = group(
        add.s(2, 2),
        add.s(4, 4),
        add.s(8, 8),
        add.s(16, 16),
    )
    
    result = workflow.apply_async()
    print(f"Group results: {result.get()}")


def chord_example():
    """Parallel tasks with callback."""
    print("\n=== Chord Example ===\n")
    
    from tasks.basic import multiply
    
    # Sum all parallel results
    @app.task
    def sum_results(results):
        return sum(results)
    
    workflow = chord(
        [add.s(i, i) for i in range(5)],  # Parallel: 0, 2, 4, 6, 8
        sum_results.s(),  # Callback: sum all = 20
    )
    
    result = workflow.apply_async()
    print(f"Chord result: {result.get()}")


# =============================================================================
# Advanced Task Options
# =============================================================================

def task_with_options():
    """Task invocation with various options."""
    print("\n=== Task Options ===\n")
    
    result = add.apply_async(
        args=(4, 4),
        kwargs={},
        # Scheduling
        countdown=0,  # Delay in seconds
        eta=None,  # Specific datetime
        expires=60,  # Task expires after 60 seconds
        
        # Routing
        queue="default",
        routing_key="default",
        priority=5,  # 0-9, higher = more priority
        
        # Retry behavior
        retry=True,
        retry_policy={
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.5,
        },
        
        # Result options
        ignore_result=False,
        
        # Headers
        headers={"custom_header": "value"},
    )
    
    print(f"Task with options: {result.get()}")


def priority_example():
    """Task priority demonstration."""
    print("\n=== Priority Example ===\n")
    
    # Lower priority
    result1 = add.apply_async(args=(1, 1), priority=1)
    
    # Higher priority
    result2 = add.apply_async(args=(2, 2), priority=9)
    
    print(f"Low priority result: {result1.get()}")
    print(f"High priority result: {result2.get()}")


# =============================================================================
# Task Revocation
# =============================================================================

def revoke_task():
    """Cancel/revoke a task."""
    print("\n=== Task Revocation ===\n")
    
    from tasks.basic import long_running_task
    
    # Start a long task
    result = long_running_task.apply_async(args=(60,))
    print(f"Started task: {result.id}")
    
    time.sleep(2)
    
    # Revoke (cancel) the task
    result.revoke(terminate=True, signal="SIGKILL")
    print(f"Task revoked")
    
    # Check status
    print(f"Status: {result.status}")


def revoke_by_id():
    """Revoke task by ID."""
    print("\n=== Revoke by ID ===\n")
    
    from celery.result import AsyncResult
    
    task_id = "some-task-id"
    
    # Revoke by ID
    app.control.revoke(task_id, terminate=True)
    
    # Or create AsyncResult and revoke
    result = AsyncResult(task_id, app=app)
    result.revoke()


# =============================================================================
# Batch Operations
# =============================================================================

def batch_tasks():
    """Submit multiple tasks efficiently."""
    print("\n=== Batch Tasks ===\n")
    
    # Method 1: Group
    batch = group(add.s(i, i) for i in range(10))
    result = batch.apply_async()
    print(f"Batch results: {result.get()}")
    
    # Method 2: Send tasks individually but efficiently
    with app.pool.acquire(block=True) as conn:
        results = []
        for i in range(10):
            result = add.apply_async(
                args=(i, i),
                connection=conn,
            )
            results.append(result)
    
    # Get all results
    values = [r.get() for r in results]
    print(f"Individual results: {values}")


# =============================================================================
# Error Handling
# =============================================================================

def handle_task_errors():
    """Handle task failures."""
    print("\n=== Error Handling ===\n")
    
    from tasks.basic import divide
    from celery.exceptions import TimeoutError
    
    try:
        # This will fail
        result = divide.delay(10, 0)
        value = result.get(timeout=10)
    except ValueError as e:
        print(f"Task raised ValueError: {e}")
    except TimeoutError:
        print("Task timed out")
    except Exception as e:
        print(f"Task failed: {e}")
    
    # Check if failed
    if result.failed():
        print(f"Task failed with: {result.result}")


def handle_with_callbacks():
    """Use link/link_error for callbacks."""
    print("\n=== Callbacks ===\n")
    
    from tasks.basic import on_success_callback, on_error_callback
    
    # Success callback
    result = add.apply_async(
        args=(2, 2),
        link=on_success_callback.s(),  # Called on success
        link_error=on_error_callback.s(),  # Called on error
    )
    
    print(f"Task result: {result.get()}")


# =============================================================================
# Worker Inspection
# =============================================================================

def inspect_workers():
    """Inspect Celery workers."""
    print("\n=== Worker Inspection ===\n")
    
    i = app.control.inspect()
    
    # Active tasks
    print("Active tasks:", i.active())
    
    # Reserved tasks
    print("Reserved tasks:", i.reserved())
    
    # Scheduled tasks (ETA)
    print("Scheduled tasks:", i.scheduled())
    
    # Registered tasks
    print("Registered tasks:", i.registered())
    
    # Worker stats
    print("Stats:", i.stats())
    
    # Ping workers
    print("Ping:", i.ping())


def control_workers():
    """Control Celery workers."""
    print("\n=== Worker Control ===\n")
    
    # Shutdown all workers
    # app.control.shutdown()
    
    # Shutdown specific worker
    # app.control.shutdown(destination=['worker1@hostname'])
    
    # Add consumer to queue
    app.control.add_consumer(
        queue="new_queue",
        destination=["celery@myhost"],
    )
    
    # Cancel consumer from queue
    app.control.cancel_consumer(
        queue="old_queue",
        destination=["celery@myhost"],
    )
    
    # Rate limit a task
    app.control.rate_limit("tasks.basic.add", "10/m")
    
    # Purge all waiting tasks
    # app.control.purge()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Celery Task Client Examples")
    print("=" * 60)
    print("""
    Run examples:
    
    1. Basic examples:      basic_examples()
    2. Task status:         check_task_status()
    3. Monitor progress:    monitor_progress()
    4. Chain example:       chain_example()
    5. Group example:       group_example()
    6. Chord example:       chord_example()
    7. Task options:        task_with_options()
    8. Batch tasks:         batch_tasks()
    9. Error handling:      handle_task_errors()
    10. Inspect workers:    inspect_workers()
    
    Make sure Celery worker is running:
        celery -A celery_app worker --loglevel=info
    """)
    
    # Run a simple example
    basic_examples()
