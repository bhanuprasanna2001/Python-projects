"""
Basic Celery Tasks
==================
Simple task definitions demonstrating core Celery features.
"""

from celery_app import app
import time
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Simple Tasks
# =============================================================================

@app.task
def add(x: int, y: int) -> int:
    """Simple addition task."""
    return x + y


@app.task
def multiply(x: int, y: int) -> int:
    """Simple multiplication task."""
    return x * y


@app.task
def divide(x: int, y: int) -> float:
    """Division task that might fail."""
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y


# =============================================================================
# Tasks with Binding (access to self)
# =============================================================================

@app.task(bind=True)
def debug_task(self):
    """
    Bound task - has access to the task instance.
    Useful for retries and accessing task metadata.
    """
    return {
        "request_id": self.request.id,
        "task_name": self.name,
        "args": self.request.args,
        "kwargs": self.request.kwargs,
        "hostname": self.request.hostname,
        "retries": self.request.retries,
    }


@app.task(bind=True)
def get_task_info(self):
    """Returns detailed information about the current task."""
    return {
        "id": self.request.id,
        "name": self.name,
        "args": self.request.args,
        "kwargs": self.request.kwargs,
        "origin": self.request.origin,
        "retries": self.request.retries,
        "delivery_info": self.request.delivery_info,
    }


# =============================================================================
# Long-Running Tasks
# =============================================================================

@app.task
def long_running_task(duration: int = 10) -> str:
    """
    Simulates a long-running task.
    In production, this could be data processing, file uploads, etc.
    """
    logger.info(f"Starting long-running task for {duration} seconds")
    time.sleep(duration)
    logger.info("Long-running task completed")
    return f"Completed after {duration} seconds"


@app.task(bind=True)
def long_task_with_progress(self, total_items: int = 100):
    """
    Long-running task that reports progress.
    """
    for i in range(total_items):
        time.sleep(0.1)  # Simulate work
        
        # Update task state with progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": total_items,
                "percent": int((i + 1) / total_items * 100),
            }
        )
    
    return {"status": "completed", "items_processed": total_items}


# =============================================================================
# Heartbeat/Health Check
# =============================================================================

@app.task
def heartbeat():
    """Simple heartbeat task for periodic health checks."""
    import datetime
    return {
        "status": "alive",
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


# =============================================================================
# Tasks with Options
# =============================================================================

@app.task(
    name="tasks.basic.rate_limited_task",  # Custom name
    rate_limit="10/m",  # 10 tasks per minute
    ignore_result=True,  # Don't store result
)
def rate_limited_task(message: str):
    """Task with rate limiting."""
    logger.info(f"Rate limited task: {message}")


@app.task(
    queue="high_priority",
    priority=9,  # Higher number = higher priority
)
def high_priority_task(data: dict):
    """High priority task routed to specific queue."""
    logger.info(f"Processing high priority: {data}")
    return {"processed": data}


@app.task(
    expires=60,  # Task expires in 60 seconds if not picked up
)
def time_sensitive_task(data: dict):
    """Task that expires if not executed quickly."""
    logger.info(f"Time sensitive task: {data}")
    return {"status": "processed"}


# =============================================================================
# Callback Tasks
# =============================================================================

@app.task
def on_success_callback(result):
    """Callback task executed on success."""
    logger.info(f"Task succeeded with result: {result}")
    return f"Callback received: {result}"


@app.task
def on_error_callback(request, exc, traceback):
    """Callback task executed on error."""
    logger.error(f"Task {request.id} failed: {exc}")
    # Could notify monitoring system, send alert, etc.
