"""
Advanced Celery Tasks
=====================
Retries, error handling, task inheritance, and advanced patterns.
"""

from celery_app import app
from celery.exceptions import (
    MaxRetriesExceededError,
    SoftTimeLimitExceeded,
    Reject,
    Ignore,
)
from celery import Task
import time
import random
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Retry Patterns
# =============================================================================

@app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,  # 1 minute
)
def task_with_retry(self, data: dict):
    """
    Task with automatic retry on failure.
    """
    try:
        # Simulate occasional failure
        if random.random() < 0.5:
            raise ConnectionError("Simulated connection error")
        return {"status": "success", "data": data}
    except ConnectionError as exc:
        logger.warning(f"Retry {self.request.retries + 1}/5: {exc}")
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=5)
def task_with_exponential_backoff(self, url: str):
    """
    Retry with exponential backoff.
    Delays: 1s, 2s, 4s, 8s, 16s
    """
    try:
        # Simulate API call that might fail
        if random.random() < 0.4:
            raise ConnectionError("API unavailable")
        return {"url": url, "status": "fetched"}
    except ConnectionError as exc:
        # Exponential backoff: 2^retries seconds
        countdown = 2 ** self.request.retries
        logger.warning(f"Retrying in {countdown}s (attempt {self.request.retries + 1})")
        raise self.retry(exc=exc, countdown=countdown)


@app.task(bind=True, max_retries=3)
def task_with_jitter(self, data: dict):
    """
    Retry with exponential backoff and jitter.
    Prevents thundering herd problem.
    """
    try:
        if random.random() < 0.5:
            raise ConnectionError("Service unavailable")
        return data
    except ConnectionError as exc:
        # Exponential backoff with jitter
        base_delay = 2 ** self.request.retries
        jitter = random.uniform(0, base_delay * 0.5)
        countdown = base_delay + jitter
        
        logger.warning(f"Retrying in {countdown:.2f}s")
        raise self.retry(exc=exc, countdown=countdown)


@app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes
    retry_jitter=True,  # Add random jitter
    max_retries=5,
)
def task_with_autoretry(self, url: str):
    """
    Using autoretry_for for automatic retry on specific exceptions.
    """
    # Simulate network request
    if random.random() < 0.3:
        raise ConnectionError(f"Failed to connect to {url}")
    return {"url": url, "status": "success"}


# =============================================================================
# Error Handling
# =============================================================================

@app.task(bind=True)
def task_with_error_handling(self, data: dict):
    """
    Comprehensive error handling patterns.
    """
    try:
        # Validate input
        if not data.get("required_field"):
            raise ValueError("Missing required field")
        
        # Process
        result = process_data(data)
        return result
        
    except ValueError as e:
        # Don't retry for validation errors
        logger.error(f"Validation error: {e}")
        return {"error": str(e), "status": "failed"}
        
    except ConnectionError as e:
        # Retry for connection errors
        logger.warning(f"Connection error, retrying: {e}")
        raise self.retry(exc=e, max_retries=3)
        
    except Exception as e:
        # Log unexpected errors
        logger.exception(f"Unexpected error: {e}")
        raise


def process_data(data: dict) -> dict:
    """Helper function."""
    return {"processed": True, **data}


@app.task(bind=True)
def task_reject_message(self, data: dict):
    """
    Reject a message (remove from queue without requeue).
    """
    if not data.get("valid"):
        # Reject the message - won't be requeued
        raise Reject("Invalid message, rejecting", requeue=False)
    return {"status": "processed"}


@app.task(bind=True)
def task_ignore_result(self, data: dict):
    """
    Ignore a task - pretend it was never received.
    """
    if data.get("skip"):
        # Task will be ignored, no result stored
        raise Ignore()
    return {"status": "processed"}


# =============================================================================
# Time Limits
# =============================================================================

@app.task(
    soft_time_limit=30,  # Soft limit: 30 seconds
    time_limit=60,  # Hard limit: 60 seconds
)
def task_with_time_limit():
    """
    Task with time limits.
    Soft limit raises SoftTimeLimitExceeded (can be caught).
    Hard limit kills the task.
    """
    try:
        # Simulate long-running work
        for i in range(100):
            time.sleep(1)
    except SoftTimeLimitExceeded:
        # Cleanup and return partial result
        logger.warning("Soft time limit reached, cleaning up")
        return {"status": "partial", "reason": "time_limit"}


# =============================================================================
# Custom Task Base Class
# =============================================================================

class BaseTask(Task):
    """
    Custom base task class with common functionality.
    """
    abstract = True
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        logger.info(f"Task {self.name}[{task_id}] succeeded")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        logger.error(f"Task {self.name}[{task_id}] failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(f"Task {self.name}[{task_id}] retrying: {exc}")
    
    def before_start(self, task_id, args, kwargs):
        """Called before task starts."""
        logger.info(f"Task {self.name}[{task_id}] starting")
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Called after task returns."""
        logger.info(f"Task {self.name}[{task_id}] returned with status {status}")


@app.task(base=BaseTask, bind=True)
def task_with_custom_base(self, data: dict):
    """Task using custom base class."""
    return {"processed": True, "data": data}


# =============================================================================
# Task State Updates
# =============================================================================

@app.task(bind=True)
def task_with_custom_states(self, items: list):
    """
    Task that uses custom states to report progress.
    """
    total = len(items)
    
    for i, item in enumerate(items):
        # Update state with progress
        self.update_state(
            state="PROCESSING",
            meta={
                "current": i + 1,
                "total": total,
                "percent": int((i + 1) / total * 100),
                "current_item": item,
            }
        )
        
        # Simulate processing
        time.sleep(0.5)
    
    return {"status": "completed", "items_processed": total}


# =============================================================================
# Scheduled/Periodic Tasks
# =============================================================================

@app.task
def cleanup_old_data():
    """Periodic task: Clean up old data."""
    logger.info("Running cleanup task")
    # Simulate cleanup
    time.sleep(1)
    return {"cleaned_records": random.randint(0, 100)}


@app.task
def generate_daily_report():
    """Periodic task: Generate daily report."""
    logger.info("Generating daily report")
    return {
        "report_type": "daily",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.task
def generate_weekly_summary():
    """Periodic task: Weekly summary."""
    logger.info("Generating weekly summary")
    return {"report_type": "weekly"}


@app.task
def monthly_cleanup():
    """Periodic task: Monthly cleanup."""
    logger.info("Running monthly cleanup")
    return {"report_type": "monthly"}


# =============================================================================
# Notification Tasks
# =============================================================================

@app.task(
    bind=True,
    queue="high_priority",
    max_retries=5,
)
def send_notification(self, user_id: int, message: str, channel: str = "email"):
    """
    High-priority notification task with retries.
    """
    try:
        # Simulate sending notification
        if random.random() < 0.2:
            raise ConnectionError("Notification service unavailable")
        
        logger.info(f"Sent {channel} notification to user {user_id}")
        return {
            "user_id": user_id,
            "channel": channel,
            "status": "sent",
        }
    except ConnectionError as exc:
        raise self.retry(exc=exc, countdown=5)


@app.task(queue="high_priority")
def send_batch_notifications(user_ids: list, message: str):
    """Send notifications to multiple users."""
    from celery import group
    
    # Create group of notification tasks
    notification_group = group(
        send_notification.s(uid, message) for uid in user_ids
    )
    
    # Execute in parallel
    return notification_group.apply_async()


# =============================================================================
# Heavy Computation Tasks
# =============================================================================

@app.task(
    queue="cpu_intensive",
    time_limit=3600,
    soft_time_limit=3300,
)
def heavy_computation(data: dict):
    """
    CPU-intensive task routed to dedicated queue.
    """
    logger.info("Starting heavy computation")
    
    # Simulate CPU-intensive work
    result = 0
    for i in range(10_000_000):
        result += i % 1000
    
    logger.info("Heavy computation completed")
    return {"result": result, "input": data}


@app.task(bind=True, queue="cpu_intensive")
def process_large_file(self, file_path: str, chunk_size: int = 1024):
    """
    Process large file with progress reporting.
    """
    import os
    
    # Simulate file processing
    total_chunks = 100
    
    for i in range(total_chunks):
        # Update progress
        self.update_state(
            state="PROCESSING",
            meta={
                "current_chunk": i + 1,
                "total_chunks": total_chunks,
                "percent": int((i + 1) / total_chunks * 100),
            }
        )
        
        # Simulate chunk processing
        time.sleep(0.1)
    
    return {
        "file": file_path,
        "status": "completed",
        "chunks_processed": total_chunks,
    }
