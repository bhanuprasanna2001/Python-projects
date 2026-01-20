"""
Celery Application Configuration
================================
Central configuration for the Celery application.
"""

from celery import Celery
from kombu import Queue

# =============================================================================
# Create Celery App
# =============================================================================

app = Celery(
    "demo_project",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=[
        "tasks.basic",
        "tasks.workflows",
        "tasks.advanced",
    ]
)


# =============================================================================
# Configuration
# =============================================================================

app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result settings
    result_expires=3600,  # Results expire in 1 hour
    result_extended=True,  # Store additional task metadata
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Reject if worker dies
    task_time_limit=3600,  # Hard time limit (1 hour)
    task_soft_time_limit=3300,  # Soft time limit (55 min)
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_concurrency=4,  # Number of worker processes
    
    # Rate limiting
    task_default_rate_limit="100/m",  # Default rate limit
    
    # Retry settings
    task_default_retry_delay=60,  # Default retry delay
    task_max_retries=3,  # Default max retries
    
    # Queue routing
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("high_priority", routing_key="high"),
        Queue("low_priority", routing_key="low"),
        Queue("cpu_intensive", routing_key="cpu"),
    ),
    task_routes={
        "tasks.basic.add": {"queue": "default"},
        "tasks.advanced.heavy_computation": {"queue": "cpu_intensive"},
        "tasks.advanced.send_notification": {"queue": "high_priority"},
    },
)


# =============================================================================
# Beat Schedule (Periodic Tasks)
# =============================================================================

from celery.schedules import crontab
from datetime import timedelta

app.conf.beat_schedule = {
    # Every 10 seconds
    "heartbeat": {
        "task": "tasks.basic.heartbeat",
        "schedule": 10.0,
    },
    
    # Every minute
    "cleanup-old-data": {
        "task": "tasks.advanced.cleanup_old_data",
        "schedule": timedelta(minutes=1),
    },
    
    # Every day at midnight
    "daily-report": {
        "task": "tasks.advanced.generate_daily_report",
        "schedule": crontab(hour=0, minute=0),
    },
    
    # Every Monday at 9 AM
    "weekly-summary": {
        "task": "tasks.advanced.generate_weekly_summary",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
    
    # First day of every month
    "monthly-cleanup": {
        "task": "tasks.advanced.monthly_cleanup",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),
    },
}


# =============================================================================
# Error Handling Hooks
# =============================================================================

from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_success,
    worker_ready,
)
import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    """Called before a task is executed."""
    logger.info(f"Task {task.name}[{task_id}] starting with args={args}")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    """Called after a task has completed."""
    logger.info(f"Task {task.name}[{task_id}] finished with state={state}")


@task_success.connect
def task_success_handler(sender, result, **kwargs):
    """Called when a task succeeds."""
    logger.info(f"Task {sender.name} succeeded with result: {result}")


@task_failure.connect
def task_failure_handler(task_id, exception, traceback, **kwargs):
    """Called when a task fails."""
    logger.error(f"Task {task_id} failed: {exception}")


@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Called when a worker is ready to accept tasks."""
    logger.info("Worker is ready!")


# =============================================================================
# Auto-discover tasks
# =============================================================================

if __name__ == "__main__":
    app.start()
