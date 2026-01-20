"""
Production-grade scheduler for automated pipeline execution.

Features:
- APScheduler integration with SQLite job store
- Cron and interval scheduling
- Job persistence across restarts
- Backfill support for historical data
- Graceful shutdown handling
"""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from etl_pipeline.config import PipelineConfig, get_project_root
from etl_pipeline.models import DataSource, JobStatus
from etl_pipeline.orchestration.job_store import get_job_store
from etl_pipeline.utils.logging import get_logger

logger = get_logger("orchestration.scheduler")


class ScheduleType(str, Enum):
    """Types of schedule triggers."""

    CRON = "cron"
    INTERVAL = "interval"


@dataclass
class ScheduleConfig:
    """
    Configuration for a scheduled pipeline job.

    Attributes:
        job_id: Unique identifier for this schedule
        pipeline_name: Name of the pipeline to run
        sources: Data sources to process
        schedule_type: CRON or INTERVAL
        cron_expression: Cron expression (for CRON type)
        interval_minutes: Interval in minutes (for INTERVAL type)
        enabled: Whether this schedule is active
        max_instances: Maximum concurrent instances
        misfire_grace_time: Seconds to wait before considering job misfired
        coalesce: Coalesce missed executions into single run
        timeout_minutes: Job timeout in minutes
    """

    job_id: str
    pipeline_name: str
    sources: list[DataSource]
    schedule_type: ScheduleType = ScheduleType.INTERVAL
    cron_expression: str | None = None  # "0 */6 * * *" = every 6 hours
    interval_minutes: int = 60
    enabled: bool = True
    max_instances: int = 1
    misfire_grace_time: int = 300  # 5 minutes
    coalesce: bool = True
    timeout_minutes: int = 30
    extra_args: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulerStats:
    """Statistics for the scheduler."""

    running: bool = False
    jobs_scheduled: int = 0
    jobs_executed: int = 0
    jobs_failed: int = 0
    last_execution: datetime | None = None
    uptime_seconds: float = 0


class PipelineScheduler:
    """
    Production scheduler for ETL pipelines.

    Provides:
    - Cron and interval-based scheduling
    - Job persistence using SQLite
    - Backfill functionality
    - Graceful shutdown
    - Execution statistics
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        job_store_path: str = "data/scheduler/scheduler_jobs.db",
    ) -> None:
        """
        Initialize the scheduler.

        Args:
            config: Pipeline configuration
            job_store_path: Path to SQLite database for job persistence
        """
        self.config = config or PipelineConfig()
        self.job_store_path = self._resolve_path(job_store_path)
        self.pipeline_job_store = get_job_store()

        # Statistics
        self._stats = SchedulerStats()
        self._start_time: datetime | None = None
        self._scheduled_configs: dict[str, ScheduleConfig] = {}

        # Initialize APScheduler
        self._scheduler = self._create_scheduler()

        # Shutdown handling
        self._shutdown_event = asyncio.Event()

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to project root."""
        p = Path(path)
        if not p.is_absolute():
            p = get_project_root() / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _create_scheduler(self) -> AsyncIOScheduler:
        """Create and configure the APScheduler instance."""
        # Job stores - use SQLite for persistence
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{self.job_store_path}")}

        # Executors
        executors = {
            "default": AsyncIOExecutor(),
        }

        # Job defaults
        job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        }

        scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )

        # Add event listeners
        scheduler.add_listener(
            self._on_job_executed,
            mask=0x800,  # EVENT_JOB_EXECUTED
        )
        scheduler.add_listener(
            self._on_job_error,
            mask=0x1000,  # EVENT_JOB_ERROR
        )

        return scheduler

    def _on_job_executed(self, event: Any) -> None:
        """Handle job execution event."""
        self._stats.jobs_executed += 1
        self._stats.last_execution = datetime.now()
        logger.info(f"Job executed: {event.job_id}")

    def _on_job_error(self, event: Any) -> None:
        """Handle job error event."""
        self._stats.jobs_failed += 1
        logger.error(f"Job failed: {event.job_id}, error: {event.exception}")

    async def _run_pipeline(
        self,
        schedule_config: ScheduleConfig,
    ) -> None:
        """
        Execute a pipeline for a scheduled job.

        Args:
            schedule_config: Configuration for this scheduled run
        """
        # Import here to avoid circular imports
        from etl_pipeline.config import get_settings
        from etl_pipeline.orchestration.pipeline import Pipeline

        logger.info(f"Starting scheduled pipeline: {schedule_config.pipeline_name}")

        try:
            # Create pipeline instance with settings
            settings = get_settings()
            pipeline = Pipeline(settings)

            # Run with timeout
            try:
                job = await asyncio.wait_for(
                    pipeline.run(sources=schedule_config.sources),
                    timeout=schedule_config.timeout_minutes * 60,
                )

                # Persist job result
                await self.pipeline_job_store.save_job(job)

                if job.status == JobStatus.COMPLETED:
                    logger.info(
                        f"Pipeline {schedule_config.pipeline_name} completed: "
                        f"{job.total_loaded} records loaded"
                    )
                else:
                    logger.warning(
                        f"Pipeline {schedule_config.pipeline_name} finished with "
                        f"status: {job.status.value}"
                    )

            except TimeoutError:
                logger.error(
                    f"Pipeline {schedule_config.pipeline_name} timed out "
                    f"after {schedule_config.timeout_minutes} minutes"
                )

        except Exception as e:
            logger.exception(f"Error running pipeline {schedule_config.pipeline_name}: {e}")

    def add_schedule(self, config: ScheduleConfig) -> bool:
        """
        Add a pipeline schedule.

        Args:
            config: Schedule configuration

        Returns:
            True if schedule was added successfully
        """
        if not config.enabled:
            logger.info(f"Schedule {config.job_id} is disabled, skipping")
            return False

        try:
            # Create trigger based on schedule type
            if config.schedule_type == ScheduleType.CRON:
                if not config.cron_expression:
                    raise ValueError("Cron expression required for CRON schedule")
                trigger = CronTrigger.from_crontab(config.cron_expression)
            else:
                trigger = IntervalTrigger(minutes=config.interval_minutes)

            # Add job to scheduler
            self._scheduler.add_job(
                self._run_pipeline,
                trigger=trigger,
                id=config.job_id,
                name=f"Pipeline: {config.pipeline_name}",
                args=[config],
                max_instances=config.max_instances,
                misfire_grace_time=config.misfire_grace_time,
                coalesce=config.coalesce,
                replace_existing=True,
            )

            self._scheduled_configs[config.job_id] = config
            self._stats.jobs_scheduled = len(self._scheduled_configs)
            logger.info(f"Added schedule: {config.job_id} ({config.schedule_type.value})")
            return True

        except Exception as e:
            logger.error(f"Failed to add schedule {config.job_id}: {e}")
            return False

    def remove_schedule(self, job_id: str) -> bool:
        """
        Remove a schedule.

        Args:
            job_id: ID of the schedule to remove

        Returns:
            True if schedule was removed
        """
        try:
            self._scheduler.remove_job(job_id)
            self._scheduled_configs.pop(job_id, None)
            self._stats.jobs_scheduled = len(self._scheduled_configs)
            logger.info(f"Removed schedule: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove schedule {job_id}: {e}")
            return False

    def get_schedules(self) -> list[dict[str, Any]]:
        """
        Get all active schedules.

        Returns:
            List of schedule information dictionaries
        """
        schedules = []
        for job in self._scheduler.get_jobs():
            config = self._scheduled_configs.get(job.id)
            schedules.append(
                {
                    "job_id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "pipeline_name": config.pipeline_name if config else None,
                    "enabled": config.enabled if config else True,
                }
            )
        return schedules

    def get_stats(self) -> SchedulerStats:
        """Get scheduler statistics."""
        if self._start_time:
            self._stats.uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        return self._stats

    async def run_now(self, job_id: str) -> bool:
        """
        Run a scheduled job immediately.

        Args:
            job_id: ID of the schedule to run

        Returns:
            True if job was triggered
        """
        config = self._scheduled_configs.get(job_id)
        if not config:
            logger.error(f"Schedule not found: {job_id}")
            return False

        logger.info(f"Running job {job_id} immediately")
        task = asyncio.create_task(self._run_pipeline(config))
        # Store task reference to prevent garbage collection
        self._active_tasks = getattr(self, "_active_tasks", set())
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return True

    async def backfill(
        self,
        config: ScheduleConfig,
        start_date: datetime,
        end_date: datetime | None = None,
        interval_hours: int = 24,
    ) -> list[str]:
        """
        Run backfill for historical data.

        Args:
            config: Schedule configuration to use
            start_date: Start of backfill period
            end_date: End of backfill period (default: now)
            interval_hours: Hours between each backfill run

        Returns:
            List of job IDs created
        """
        end_date = end_date or datetime.now()
        job_ids = []
        current = start_date

        logger.info(
            f"Starting backfill from {start_date} to {end_date} with {interval_hours}h intervals"
        )

        while current < end_date:
            # Create a modified config for this backfill window
            backfill_config = ScheduleConfig(
                job_id=f"{config.job_id}_backfill_{current.strftime('%Y%m%d_%H%M')}",
                pipeline_name=config.pipeline_name,
                sources=config.sources,
                timeout_minutes=config.timeout_minutes,
                extra_args={
                    **config.extra_args,
                    "backfill_start": current.isoformat(),
                    "backfill_end": (current + timedelta(hours=interval_hours)).isoformat(),
                },
            )

            # Run the backfill job
            await self._run_pipeline(backfill_config)
            job_ids.append(backfill_config.job_id)

            current += timedelta(hours=interval_hours)

        logger.info(f"Backfill completed: {len(job_ids)} jobs executed")
        return job_ids

    def start(self) -> None:
        """Start the scheduler."""
        if self._scheduler.running:
            logger.warning("Scheduler is already running")
            return

        self._scheduler.start()
        self._start_time = datetime.now()
        self._stats.running = True
        logger.info("Scheduler started")

    def stop(self, wait: bool = True) -> None:
        """
        Stop the scheduler.

        Args:
            wait: Wait for running jobs to complete
        """
        if not self._scheduler.running:
            logger.warning("Scheduler is not running")
            return

        self._scheduler.shutdown(wait=wait)
        self._stats.running = False
        self._shutdown_event.set()
        logger.info("Scheduler stopped")

    def pause(self) -> None:
        """Pause all job execution."""
        self._scheduler.pause()
        logger.info("Scheduler paused")

    def resume(self) -> None:
        """Resume job execution."""
        self._scheduler.resume()
        logger.info("Scheduler resumed")

    async def run_forever(self) -> None:
        """
        Run the scheduler until shutdown signal.

        Handles SIGINT and SIGTERM for graceful shutdown.
        """
        # Set up signal handlers
        loop = asyncio.get_event_loop()

        def signal_handler():
            logger.info("Shutdown signal received")
            self.stop(wait=True)

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        # Start scheduler
        self.start()

        # Wait for shutdown
        await self._shutdown_event.wait()
        logger.info("Scheduler shutdown complete")


# Factory function for creating default schedule configs
def create_default_schedules(
    sources: list[DataSource],
) -> list[ScheduleConfig]:
    """
    Create default schedule configurations.

    Args:
        sources: Data sources for the pipelines

    Returns:
        List of default schedule configurations
    """
    return [
        # Every hour
        ScheduleConfig(
            job_id="hourly_pipeline",
            pipeline_name="Hourly Data Sync",
            sources=sources,
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=60,
        ),
        # Daily at midnight
        ScheduleConfig(
            job_id="daily_pipeline",
            pipeline_name="Daily Full Sync",
            sources=sources,
            schedule_type=ScheduleType.CRON,
            cron_expression="0 0 * * *",
            timeout_minutes=120,
        ),
        # Every 6 hours
        ScheduleConfig(
            job_id="sixhourly_pipeline",
            pipeline_name="6-Hour Incremental Sync",
            sources=sources,
            schedule_type=ScheduleType.CRON,
            cron_expression="0 */6 * * *",
        ),
    ]


# Global scheduler instance
_scheduler: PipelineScheduler | None = None


def get_scheduler() -> PipelineScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PipelineScheduler()
    return _scheduler
