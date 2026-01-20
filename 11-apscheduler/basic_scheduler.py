"""
APScheduler Basic Examples
==========================
Demonstrates fundamental scheduler concepts and usage patterns.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    EVENT_JOB_ADDED,
    EVENT_JOB_REMOVED,
)
import logging
from datetime import datetime, timedelta
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Job Functions
# =============================================================================

def simple_job():
    """A simple job that prints current time."""
    logger.info(f"Simple job executed at {datetime.now()}")


def job_with_args(name: str, count: int):
    """Job that accepts arguments."""
    logger.info(f"Job with args: name={name}, count={count}")


def job_with_return():
    """Job that returns a value (stored by listeners)."""
    result = datetime.now().isoformat()
    logger.info(f"Job returning: {result}")
    return result


def slow_job(duration: int = 5):
    """A slow job for demonstrating overlapping."""
    logger.info(f"Slow job starting, will take {duration}s")
    time.sleep(duration)
    logger.info("Slow job completed")


def failing_job():
    """A job that fails sometimes."""
    import random
    if random.random() < 0.3:
        raise ValueError("Simulated failure!")
    logger.info("Failing job succeeded this time")


# =============================================================================
# Background Scheduler
# =============================================================================

def background_scheduler_example():
    """
    BackgroundScheduler runs jobs in the background.
    Non-blocking - your main code continues to run.
    """
    logger.info("=== Background Scheduler Example ===")
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Add jobs
    scheduler.add_job(
        simple_job,
        trigger="interval",
        seconds=5,
        id="simple_job",
        name="Simple Job",
    )
    
    scheduler.add_job(
        job_with_args,
        trigger="interval",
        seconds=10,
        args=("World",),
        kwargs={"count": 42},
        id="job_with_args",
    )
    
    # Start scheduler
    scheduler.start()
    
    try:
        # Main thread continues running
        logger.info("Scheduler running in background. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


# =============================================================================
# Blocking Scheduler
# =============================================================================

def blocking_scheduler_example():
    """
    BlockingScheduler blocks the main thread.
    Use for scripts where scheduler is the main activity.
    """
    logger.info("=== Blocking Scheduler Example ===")
    
    scheduler = BlockingScheduler()
    
    # Add jobs before starting
    scheduler.add_job(
        simple_job,
        trigger="interval",
        seconds=3,
        id="blocking_simple",
    )
    
    logger.info("Starting blocking scheduler...")
    
    try:
        # This will block until shutdown
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")


# =============================================================================
# Job Management
# =============================================================================

def job_management_example():
    """Demonstrates adding, removing, pausing, and resuming jobs."""
    logger.info("=== Job Management Example ===")
    
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # Add a job
    job = scheduler.add_job(
        simple_job,
        trigger="interval",
        seconds=2,
        id="managed_job",
    )
    logger.info(f"Added job: {job.id}")
    
    time.sleep(5)
    
    # Pause the job
    scheduler.pause_job("managed_job")
    logger.info("Job paused")
    
    time.sleep(5)
    
    # Resume the job
    scheduler.resume_job("managed_job")
    logger.info("Job resumed")
    
    time.sleep(5)
    
    # Modify the job
    scheduler.modify_job(
        "managed_job",
        trigger=IntervalTrigger(seconds=1),
    )
    logger.info("Job modified to run every 1 second")
    
    time.sleep(5)
    
    # Reschedule with new trigger
    scheduler.reschedule_job(
        "managed_job",
        trigger="interval",
        seconds=3,
    )
    logger.info("Job rescheduled to every 3 seconds")
    
    time.sleep(10)
    
    # Remove the job
    scheduler.remove_job("managed_job")
    logger.info("Job removed")
    
    # List remaining jobs
    jobs = scheduler.get_jobs()
    logger.info(f"Remaining jobs: {len(jobs)}")
    
    scheduler.shutdown()


# =============================================================================
# Event Listeners
# =============================================================================

def event_listener_example():
    """Demonstrates event listeners for job monitoring."""
    logger.info("=== Event Listener Example ===")
    
    scheduler = BackgroundScheduler()
    
    # Define event listeners
    def job_executed_listener(event):
        """Called when a job is successfully executed."""
        logger.info(
            f"Job executed: {event.job_id} "
            f"at {event.scheduled_run_time} "
            f"returned: {event.retval}"
        )
    
    def job_error_listener(event):
        """Called when a job raises an exception."""
        logger.error(
            f"Job error: {event.job_id} "
            f"exception: {event.exception}"
        )
    
    def job_missed_listener(event):
        """Called when a job execution is missed."""
        logger.warning(
            f"Job missed: {event.job_id} "
            f"scheduled at: {event.scheduled_run_time}"
        )
    
    def job_added_listener(event):
        """Called when a job is added."""
        logger.info(f"Job added: {event.job_id}")
    
    def job_removed_listener(event):
        """Called when a job is removed."""
        logger.info(f"Job removed: {event.job_id}")
    
    # Register listeners
    scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
    scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
    scheduler.add_listener(job_missed_listener, EVENT_JOB_MISSED)
    scheduler.add_listener(job_added_listener, EVENT_JOB_ADDED)
    scheduler.add_listener(job_removed_listener, EVENT_JOB_REMOVED)
    
    # Add jobs
    scheduler.add_job(job_with_return, "interval", seconds=3, id="returning_job")
    scheduler.add_job(failing_job, "interval", seconds=5, id="failing_job")
    
    scheduler.start()
    
    try:
        time.sleep(30)
    finally:
        scheduler.shutdown()


# =============================================================================
# Max Instances (Prevent Overlapping)
# =============================================================================

def max_instances_example():
    """
    Demonstrates max_instances to prevent job overlapping.
    """
    logger.info("=== Max Instances Example ===")
    
    scheduler = BackgroundScheduler()
    
    # Job runs every 2 seconds but takes 5 seconds
    # Without max_instances, jobs would pile up
    scheduler.add_job(
        slow_job,
        trigger="interval",
        seconds=2,
        args=(5,),
        id="slow_job",
        max_instances=1,  # Only one instance at a time
        coalesce=True,    # Combine missed runs into one
    )
    
    scheduler.start()
    
    try:
        logger.info("Running with max_instances=1...")
        time.sleep(20)
    finally:
        scheduler.shutdown()


# =============================================================================
# Misfire Grace Time
# =============================================================================

def misfire_handling_example():
    """
    Demonstrates handling of missed job executions.
    """
    logger.info("=== Misfire Handling Example ===")
    
    scheduler = BackgroundScheduler()
    
    def important_job():
        logger.info(f"Important job at {datetime.now()}")
    
    # Job with misfire grace time
    scheduler.add_job(
        important_job,
        trigger="interval",
        seconds=5,
        id="important_job",
        misfire_grace_time=30,  # Allow up to 30s late
        coalesce=True,          # Combine missed runs
        max_instances=1,
    )
    
    scheduler.start()
    
    try:
        time.sleep(15)
        
        # Simulate blocking that causes misfire
        logger.info("Simulating block...")
        time.sleep(10)
        
        time.sleep(15)
    finally:
        scheduler.shutdown()


# =============================================================================
# One-Time Jobs
# =============================================================================

def one_time_job_example():
    """Schedule a job to run once at a specific time."""
    logger.info("=== One-Time Job Example ===")
    
    scheduler = BackgroundScheduler()
    
    def one_time_task(message: str):
        logger.info(f"One-time task executed: {message}")
    
    # Schedule for 5 seconds from now
    run_time = datetime.now() + timedelta(seconds=5)
    
    scheduler.add_job(
        one_time_task,
        trigger="date",
        run_date=run_time,
        args=("Hello from the future!",),
        id="one_time",
    )
    
    logger.info(f"Job scheduled for {run_time}")
    
    scheduler.start()
    
    try:
        time.sleep(10)
    finally:
        scheduler.shutdown()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("APScheduler Basic Examples")
    print("=" * 60)
    print("""
    Choose an example to run:
    
    1. background_scheduler_example()  - Background scheduler
    2. blocking_scheduler_example()    - Blocking scheduler
    3. job_management_example()        - Add/remove/pause jobs
    4. event_listener_example()        - Job event listeners
    5. max_instances_example()         - Prevent overlapping
    6. misfire_handling_example()      - Handle missed jobs
    7. one_time_job_example()          - One-time scheduled job
    """)
    
    # Run default example
    background_scheduler_example()
