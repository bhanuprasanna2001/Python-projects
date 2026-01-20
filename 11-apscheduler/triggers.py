"""
APScheduler Triggers
====================
Demonstrates different trigger types for scheduling jobs.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.combining import AndTrigger, OrTrigger
from datetime import datetime, timedelta
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def job_function(trigger_type: str):
    """Sample job function."""
    logger.info(f"[{trigger_type}] Job executed at {datetime.now()}")


# =============================================================================
# Interval Trigger
# =============================================================================

def interval_trigger_examples():
    """
    IntervalTrigger: Run job at fixed intervals.
    """
    logger.info("=== Interval Trigger Examples ===")
    
    scheduler = BackgroundScheduler()
    
    # Every 5 seconds
    scheduler.add_job(
        job_function,
        IntervalTrigger(seconds=5),
        args=("5s interval",),
        id="interval_5s",
    )
    
    # Every 2 minutes
    scheduler.add_job(
        job_function,
        IntervalTrigger(minutes=2),
        args=("2m interval",),
        id="interval_2m",
    )
    
    # Combined: every 1 hour and 30 minutes
    scheduler.add_job(
        job_function,
        IntervalTrigger(hours=1, minutes=30),
        args=("1h30m interval",),
        id="interval_1h30m",
    )
    
    # With start and end date
    scheduler.add_job(
        job_function,
        IntervalTrigger(
            seconds=10,
            start_date=datetime.now() + timedelta(seconds=5),
            end_date=datetime.now() + timedelta(minutes=1),
        ),
        args=("bounded interval",),
        id="interval_bounded",
    )
    
    # With jitter (randomize execution time)
    scheduler.add_job(
        job_function,
        IntervalTrigger(seconds=10, jitter=3),  # ±3 seconds
        args=("jittered interval",),
        id="interval_jittered",
    )
    
    scheduler.start()
    
    try:
        time.sleep(60)
    finally:
        scheduler.shutdown()


# =============================================================================
# Cron Trigger
# =============================================================================

def cron_trigger_examples():
    """
    CronTrigger: Run job at specific times using cron-like expressions.
    
    Cron fields:
    - year: 4-digit year
    - month: 1-12
    - day: 1-31
    - week: 1-53 (ISO week)
    - day_of_week: 0-6 or mon-sun
    - hour: 0-23
    - minute: 0-59
    - second: 0-59
    """
    logger.info("=== Cron Trigger Examples ===")
    
    scheduler = BackgroundScheduler()
    
    # Every minute
    scheduler.add_job(
        job_function,
        CronTrigger(second=0),  # At second 0 of every minute
        args=("every minute",),
        id="cron_minute",
    )
    
    # Every 5 minutes
    scheduler.add_job(
        job_function,
        CronTrigger(minute="*/5", second=0),
        args=("every 5 minutes",),
        id="cron_5min",
    )
    
    # Every hour at minute 30
    scheduler.add_job(
        job_function,
        CronTrigger(minute=30, second=0),
        args=("every hour at :30",),
        id="cron_hourly",
    )
    
    # Daily at midnight
    scheduler.add_job(
        job_function,
        CronTrigger(hour=0, minute=0, second=0),
        args=("daily at midnight",),
        id="cron_daily_midnight",
    )
    
    # Daily at 9 AM
    scheduler.add_job(
        job_function,
        CronTrigger(hour=9, minute=0, second=0),
        args=("daily at 9 AM",),
        id="cron_daily_9am",
    )
    
    # Every Monday at 9 AM
    scheduler.add_job(
        job_function,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        args=("every Monday 9 AM",),
        id="cron_monday",
    )
    
    # Weekdays at 6 PM
    scheduler.add_job(
        job_function,
        CronTrigger(day_of_week="mon-fri", hour=18, minute=0),
        args=("weekdays 6 PM",),
        id="cron_weekdays",
    )
    
    # First day of every month
    scheduler.add_job(
        job_function,
        CronTrigger(day=1, hour=0, minute=0),
        args=("1st of month",),
        id="cron_monthly",
    )
    
    # Last day of every month
    scheduler.add_job(
        job_function,
        CronTrigger(day="last", hour=23, minute=59),
        args=("last day of month",),
        id="cron_last_day",
    )
    
    # Every 15th of months Jan, Apr, Jul, Oct (quarterly)
    scheduler.add_job(
        job_function,
        CronTrigger(month="1,4,7,10", day=15, hour=9),
        args=("quarterly report",),
        id="cron_quarterly",
    )
    
    # Using cron expression string
    scheduler.add_job(
        job_function,
        CronTrigger.from_crontab("0 9 * * 1-5"),  # 9 AM weekdays
        args=("from crontab",),
        id="cron_from_crontab",
    )
    
    # With timezone
    from pytz import timezone
    scheduler.add_job(
        job_function,
        CronTrigger(hour=9, timezone=timezone("US/Eastern")),
        args=("9 AM Eastern",),
        id="cron_timezone",
    )
    
    scheduler.start()
    
    try:
        logger.info("Scheduler running. Check jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  {job.id}: next run at {job.next_run_time}")
        time.sleep(120)
    finally:
        scheduler.shutdown()


# =============================================================================
# Date Trigger
# =============================================================================

def date_trigger_examples():
    """
    DateTrigger: Run job once at a specific date/time.
    """
    logger.info("=== Date Trigger Examples ===")
    
    scheduler = BackgroundScheduler()
    
    # Run at specific datetime
    specific_time = datetime.now() + timedelta(seconds=5)
    scheduler.add_job(
        job_function,
        DateTrigger(run_date=specific_time),
        args=("specific time",),
        id="date_specific",
    )
    logger.info(f"Job scheduled for {specific_time}")
    
    # Run at specific time string
    scheduler.add_job(
        job_function,
        DateTrigger(run_date="2024-12-31 23:59:59"),
        args=("new year's eve",),
        id="date_string",
    )
    
    # Run in 10 seconds (using date string)
    scheduler.add_job(
        job_function,
        "date",
        run_date=datetime.now() + timedelta(seconds=10),
        args=("shorthand",),
        id="date_shorthand",
    )
    
    scheduler.start()
    
    try:
        time.sleep(20)
    finally:
        scheduler.shutdown()


# =============================================================================
# Combining Triggers
# =============================================================================

def combining_triggers_examples():
    """
    Combine multiple triggers using AndTrigger and OrTrigger.
    """
    logger.info("=== Combining Triggers Examples ===")
    
    scheduler = BackgroundScheduler()
    
    # OrTrigger: Run if ANY trigger fires
    # Run every 10 seconds OR every minute at :30
    or_trigger = OrTrigger([
        IntervalTrigger(seconds=10),
        CronTrigger(second=30),
    ])
    
    scheduler.add_job(
        job_function,
        or_trigger,
        args=("OR trigger",),
        id="or_trigger",
    )
    
    # AndTrigger: Run only when ALL triggers would fire
    # This is less common but useful for complex scheduling
    # Note: AndTrigger requires all triggers to have the same next fire time
    
    scheduler.start()
    
    try:
        time.sleep(60)
    finally:
        scheduler.shutdown()


# =============================================================================
# Custom Trigger
# =============================================================================

from apscheduler.triggers.base import BaseTrigger

class RandomIntervalTrigger(BaseTrigger):
    """
    Custom trigger that fires at random intervals.
    """
    
    def __init__(self, min_seconds: int = 5, max_seconds: int = 15):
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
    
    def get_next_fire_time(self, previous_fire_time, now):
        """Calculate next fire time."""
        import random
        
        interval = random.randint(self.min_seconds, self.max_seconds)
        
        if previous_fire_time is None:
            return now + timedelta(seconds=interval)
        
        return previous_fire_time + timedelta(seconds=interval)


def custom_trigger_example():
    """Demonstrate custom trigger."""
    logger.info("=== Custom Trigger Example ===")
    
    scheduler = BackgroundScheduler()
    
    scheduler.add_job(
        job_function,
        RandomIntervalTrigger(min_seconds=3, max_seconds=8),
        args=("random interval",),
        id="random_interval",
    )
    
    scheduler.start()
    
    try:
        time.sleep(60)
    finally:
        scheduler.shutdown()


# =============================================================================
# Trigger Inspection
# =============================================================================

def inspect_triggers():
    """Inspect trigger properties and next run times."""
    logger.info("=== Trigger Inspection ===")
    
    # Create triggers
    interval = IntervalTrigger(hours=2, minutes=30)
    cron = CronTrigger(hour=9, minute=0, day_of_week="mon-fri")
    date = DateTrigger(run_date=datetime(2024, 12, 31, 23, 59))
    
    # Get next fire times
    now = datetime.now()
    
    logger.info(f"Interval trigger next: {interval.get_next_fire_time(None, now)}")
    logger.info(f"Cron trigger next: {cron.get_next_fire_time(None, now)}")
    logger.info(f"Date trigger next: {date.get_next_fire_time(None, now)}")
    
    # Cron trigger field inspection
    logger.info("\nCron trigger fields:")
    for field in cron.fields:
        logger.info(f"  {field.name}: {field}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("APScheduler Trigger Examples")
    print("=" * 60)
    print("""
    Choose an example:
    
    1. interval_trigger_examples()   - Fixed interval triggers
    2. cron_trigger_examples()       - Cron-like triggers
    3. date_trigger_examples()       - One-time triggers
    4. combining_triggers_examples() - Combined triggers
    5. custom_trigger_example()      - Custom trigger class
    6. inspect_triggers()            - Inspect trigger properties
    """)
    
    # Run cron examples
    cron_trigger_examples()
