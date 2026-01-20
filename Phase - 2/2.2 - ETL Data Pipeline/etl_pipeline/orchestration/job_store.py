"""
Persistent job store for tracking pipeline executions.

Provides:
- SQLite-backed job persistence
- Job history tracking
- Job status queries
- Metrics aggregation across runs
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import aiosqlite

from etl_pipeline.config import get_project_root
from etl_pipeline.models import JobStatus, PipelineJob, Stage, StageResult
from etl_pipeline.utils.logging import get_logger

logger = get_logger("orchestration.job_store")


class JobStore:
    """
    Persistent storage for pipeline job records.

    Features:
    - SQLite-backed persistence
    - Async operations
    - Job history queries
    - Aggregated statistics
    """

    def __init__(self, database_path: str | Path = "data/jobs/job_store.db") -> None:
        """
        Initialize job store.

        Args:
            database_path: Path to SQLite database for job storage
        """
        self.database_path = self._resolve_path(database_path)
        self._initialized = False

    def _resolve_path(self, path: str | Path) -> Path:
        """Resolve path relative to project root."""
        p = Path(path)
        if not p.is_absolute():
            p = get_project_root() / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    async def initialize(self) -> None:
        """Create database schema if it doesn't exist."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.database_path) as db:
            # Jobs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    pipeline_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    total_extracted INTEGER DEFAULT 0,
                    total_transformed INTEGER DEFAULT 0,
                    total_loaded INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    config_snapshot TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Stages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS job_stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    record_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    metrics TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            """)

            # Index for faster queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_started_at ON jobs(started_at)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_stages_job_id ON job_stages(job_id)
            """)

            await db.commit()

        self._initialized = True
        logger.info(f"Job store initialized: {self.database_path}")

    async def save_job(self, job: PipelineJob) -> None:
        """
        Save or update a pipeline job.

        Args:
            job: The job to save
        """
        await self.initialize()

        async with aiosqlite.connect(self.database_path) as db:
            # Upsert job
            await db.execute(
                """
                INSERT INTO jobs (
                    job_id, pipeline_name, status, started_at, completed_at,
                    total_extracted, total_transformed, total_loaded,
                    error_count, config_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    completed_at = excluded.completed_at,
                    total_extracted = excluded.total_extracted,
                    total_transformed = excluded.total_transformed,
                    total_loaded = excluded.total_loaded,
                    error_count = excluded.error_count
            """,
                (
                    str(job.job_id),
                    job.pipeline_name,
                    job.status.value,
                    job.started_at.isoformat(),
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.total_extracted,
                    job.total_transformed,
                    job.total_loaded,
                    job.error_count,
                    json.dumps(job.config_snapshot),
                ),
            )

            # Save stages
            for stage_result in job.stages:
                await db.execute(
                    """
                    INSERT INTO job_stages (
                        job_id, stage, status, started_at, completed_at,
                        record_count, error_message, metrics
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(job.job_id),
                        stage_result.stage.value,
                        stage_result.status.value,
                        stage_result.started_at.isoformat(),
                        stage_result.completed_at.isoformat()
                        if stage_result.completed_at
                        else None,
                        stage_result.record_count,
                        stage_result.error_message,
                        json.dumps(stage_result.metrics),
                    ),
                )

            await db.commit()

        logger.debug(f"Saved job {job.job_id}")

    async def get_job(self, job_id: str | UUID) -> PipelineJob | None:
        """
        Retrieve a job by ID.

        Args:
            job_id: The job ID to look up

        Returns:
            PipelineJob if found, None otherwise
        """
        await self.initialize()

        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row

            # Get job
            cursor = await db.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),))
            row = await cursor.fetchone()

            if not row:
                return None

            # Get stages
            cursor = await db.execute(
                "SELECT * FROM job_stages WHERE job_id = ? ORDER BY started_at", (str(job_id),)
            )
            stage_rows = await cursor.fetchall()

            return self._row_to_job(dict(row), [dict(r) for r in stage_rows])

    async def get_recent_jobs(
        self,
        limit: int = 20,
        status: JobStatus | None = None,
    ) -> list[PipelineJob]:
        """
        Get recent jobs.

        Args:
            limit: Maximum number of jobs to return
            status: Filter by status (optional)

        Returns:
            List of recent jobs
        """
        await self.initialize()

        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row

            if status:
                cursor = await db.execute(
                    """SELECT * FROM jobs WHERE status = ?
                       ORDER BY started_at DESC LIMIT ?""",
                    (status.value, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM jobs ORDER BY started_at DESC LIMIT ?", (limit,)
                )

            job_rows = await cursor.fetchall()
            jobs = []

            for job_row in job_rows:
                cursor = await db.execute(
                    "SELECT * FROM job_stages WHERE job_id = ? ORDER BY started_at",
                    (job_row["job_id"],),
                )
                stage_rows = await cursor.fetchall()
                jobs.append(self._row_to_job(dict(job_row), [dict(r) for r in stage_rows]))

            return jobs

    async def get_job_stats(self) -> dict[str, Any]:
        """
        Get aggregate statistics across all jobs.

        Returns:
            Dictionary with job statistics
        """
        await self.initialize()

        async with aiosqlite.connect(self.database_path) as db:
            # Total jobs by status
            cursor = await db.execute("""
                SELECT status, COUNT(*) as count
                FROM jobs
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in await cursor.fetchall()}

            # Total records processed
            cursor = await db.execute("""
                SELECT
                    SUM(total_extracted) as extracted,
                    SUM(total_transformed) as transformed,
                    SUM(total_loaded) as loaded
                FROM jobs
            """)
            row = await cursor.fetchone()
            if row is not None:
                totals = {
                    "extracted": row[0] or 0,
                    "transformed": row[1] or 0,
                    "loaded": row[2] or 0,
                }
            else:
                totals = {"extracted": 0, "transformed": 0, "loaded": 0}

            # Average duration for completed jobs
            cursor = await db.execute("""
                SELECT AVG(
                    julianday(completed_at) - julianday(started_at)
                ) * 86400 as avg_duration_seconds
                FROM jobs
                WHERE status = 'completed' AND completed_at IS NOT NULL
            """)
            row = await cursor.fetchone()
            avg_duration = row[0] if row and row[0] else 0

            # Recent success rate (last 20 jobs)
            cursor = await db.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful
                FROM (
                    SELECT status FROM jobs ORDER BY started_at DESC LIMIT 20
                )
            """)
            row = await cursor.fetchone()
            success_rate = (row[1] / row[0] * 100) if row and row[0] > 0 else 0

            return {
                "total_jobs": sum(status_counts.values()),
                "by_status": status_counts,
                "total_records": totals,
                "avg_duration_seconds": round(avg_duration, 2),
                "recent_success_rate_percent": round(success_rate, 1),
            }

    async def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Delete jobs older than specified days.

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of deleted jobs
        """
        await self.initialize()

        async with aiosqlite.connect(self.database_path) as db:
            # Get count of jobs to delete
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM jobs
                WHERE datetime(started_at) < datetime('now', ?)
            """,
                (f"-{days} days",),
            )
            row = await cursor.fetchone()
            count = row[0] if row else 0

            if count > 0:
                # Delete stages first (foreign key)
                await db.execute(
                    """
                    DELETE FROM job_stages
                    WHERE job_id IN (
                        SELECT job_id FROM jobs
                        WHERE datetime(started_at) < datetime('now', ?)
                    )
                """,
                    (f"-{days} days",),
                )

                # Delete jobs
                await db.execute(
                    """
                    DELETE FROM jobs
                    WHERE datetime(started_at) < datetime('now', ?)
                """,
                    (f"-{days} days",),
                )

                await db.commit()
                logger.info(f"Cleaned up {count} old jobs")

            return count

    def _row_to_job(
        self,
        job_row: dict[str, Any],
        stage_rows: list[dict[str, Any]],
    ) -> PipelineJob:
        """Convert database rows to PipelineJob."""
        stages = []
        for sr in stage_rows:
            stages.append(
                StageResult(
                    stage=Stage(sr["stage"]),
                    status=JobStatus(sr["status"]),
                    started_at=datetime.fromisoformat(sr["started_at"]),
                    completed_at=datetime.fromisoformat(sr["completed_at"])
                    if sr["completed_at"]
                    else None,
                    record_count=sr["record_count"],
                    error_message=sr["error_message"],
                    metrics=json.loads(sr["metrics"]) if sr["metrics"] else {},
                )
            )

        return PipelineJob(
            job_id=UUID(job_row["job_id"]),
            pipeline_name=job_row["pipeline_name"],
            status=JobStatus(job_row["status"]),
            started_at=datetime.fromisoformat(job_row["started_at"]),
            completed_at=datetime.fromisoformat(job_row["completed_at"])
            if job_row["completed_at"]
            else None,
            stages=stages,
            total_extracted=job_row["total_extracted"],
            total_transformed=job_row["total_transformed"],
            total_loaded=job_row["total_loaded"],
            error_count=job_row["error_count"],
            config_snapshot=json.loads(job_row["config_snapshot"])
            if job_row["config_snapshot"]
            else {},
        )


# Global job store instance
_job_store: JobStore | None = None


def get_job_store() -> JobStore:
    """Get or create the global job store."""
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store
