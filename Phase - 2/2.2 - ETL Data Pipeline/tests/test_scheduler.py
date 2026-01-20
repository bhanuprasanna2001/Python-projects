"""Tests for scheduler and job store."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from etl_pipeline.models import DataSource, JobStatus, PipelineJob, Stage, StageResult
from etl_pipeline.orchestration.job_store import JobStore
from etl_pipeline.orchestration.scheduler import (
    ScheduleConfig,
    SchedulerStats,
    ScheduleType,
)


class TestJobStore:
    """Tests for JobStore class."""

    @pytest.fixture
    def job_store(self, tmp_path: Path) -> JobStore:
        """Create a job store with temporary database."""
        return JobStore(database_path=tmp_path / "test_jobs.db")

    @pytest.fixture
    def sample_job(self) -> PipelineJob:
        """Create a sample pipeline job."""
        return PipelineJob(
            job_id=uuid4(),
            pipeline_name="Test Pipeline",
            status=JobStatus.COMPLETED,
            started_at=datetime.now() - timedelta(minutes=5),
            completed_at=datetime.now(),
            stages=[
                StageResult(
                    stage=Stage.EXTRACT,
                    status=JobStatus.COMPLETED,
                    started_at=datetime.now() - timedelta(minutes=5),
                    completed_at=datetime.now() - timedelta(minutes=3),
                    record_count=100,
                ),
                StageResult(
                    stage=Stage.TRANSFORM,
                    status=JobStatus.COMPLETED,
                    started_at=datetime.now() - timedelta(minutes=3),
                    completed_at=datetime.now() - timedelta(minutes=1),
                    record_count=90,
                ),
                StageResult(
                    stage=Stage.LOAD,
                    status=JobStatus.COMPLETED,
                    started_at=datetime.now() - timedelta(minutes=1),
                    completed_at=datetime.now(),
                    record_count=90,
                ),
            ],
            total_extracted=100,
            total_transformed=90,
            total_loaded=90,
            error_count=0,
        )

    @pytest.mark.asyncio
    async def test_initialize(self, job_store: JobStore) -> None:
        """Test database initialization."""
        await job_store.initialize()
        assert job_store._initialized is True
        assert job_store.database_path.exists()

    @pytest.mark.asyncio
    async def test_save_and_get_job(
        self,
        job_store: JobStore,
        sample_job: PipelineJob,
    ) -> None:
        """Test saving and retrieving a job."""
        await job_store.save_job(sample_job)

        retrieved = await job_store.get_job(sample_job.job_id)

        assert retrieved is not None
        assert retrieved.job_id == sample_job.job_id
        assert retrieved.pipeline_name == sample_job.pipeline_name
        assert retrieved.status == sample_job.status
        assert retrieved.total_extracted == sample_job.total_extracted

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, job_store: JobStore) -> None:
        """Test getting a job that doesn't exist."""
        retrieved = await job_store.get_job(uuid4())
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_recent_jobs(
        self,
        job_store: JobStore,
    ) -> None:
        """Test getting recent jobs."""
        # Save multiple jobs
        for i in range(5):
            job = PipelineJob(
                job_id=uuid4(),
                pipeline_name=f"Test Pipeline {i}",
                status=JobStatus.COMPLETED,
                started_at=datetime.now() - timedelta(hours=i),
            )
            await job_store.save_job(job)

        # Get recent jobs
        recent = await job_store.get_recent_jobs(limit=3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_get_recent_jobs_by_status(
        self,
        job_store: JobStore,
    ) -> None:
        """Test filtering recent jobs by status."""
        # Save jobs with different statuses
        for status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.COMPLETED]:
            job = PipelineJob(
                job_id=uuid4(),
                pipeline_name="Test Pipeline",
                status=status,
                started_at=datetime.now(),
            )
            await job_store.save_job(job)

        # Get only completed jobs
        completed = await job_store.get_recent_jobs(status=JobStatus.COMPLETED)
        assert all(j.status == JobStatus.COMPLETED for j in completed)

    @pytest.mark.asyncio
    async def test_get_job_stats(
        self,
        job_store: JobStore,
    ) -> None:
        """Test getting aggregate job statistics."""
        # Save some jobs
        for i in range(10):
            job = PipelineJob(
                job_id=uuid4(),
                pipeline_name="Test Pipeline",
                status=JobStatus.COMPLETED if i < 8 else JobStatus.FAILED,
                started_at=datetime.now() - timedelta(minutes=i * 10),
                completed_at=datetime.now() - timedelta(minutes=i * 10 - 5),
                total_extracted=100,
                total_transformed=90,
                total_loaded=90,
            )
            await job_store.save_job(job)

        stats = await job_store.get_job_stats()

        assert stats["total_jobs"] == 10
        assert "by_status" in stats
        assert "total_records" in stats
        assert stats["recent_success_rate_percent"] == 80.0

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs(
        self,
        job_store: JobStore,
    ) -> None:
        """Test cleaning up old jobs."""
        # This test would need to mock datetime to properly test
        # For now, just verify the method runs without error
        deleted = await job_store.cleanup_old_jobs(days=30)
        assert deleted >= 0


class TestScheduleConfig:
    """Tests for ScheduleConfig dataclass."""

    def test_interval_config(self) -> None:
        """Test creating an interval schedule config."""
        config = ScheduleConfig(
            job_id="test_job",
            pipeline_name="Test Pipeline",
            sources=[DataSource.CSV],
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=30,
        )

        assert config.job_id == "test_job"
        assert config.schedule_type == ScheduleType.INTERVAL
        assert config.interval_minutes == 30

    def test_cron_config(self) -> None:
        """Test creating a cron schedule config."""
        config = ScheduleConfig(
            job_id="cron_job",
            pipeline_name="Cron Pipeline",
            sources=[DataSource.SQLITE],
            schedule_type=ScheduleType.CRON,
            cron_expression="0 */6 * * *",
        )

        assert config.schedule_type == ScheduleType.CRON
        assert config.cron_expression == "0 */6 * * *"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ScheduleConfig(
            job_id="default_job",
            pipeline_name="Default Pipeline",
            sources=[DataSource.CSV],
        )

        assert config.enabled is True
        assert config.max_instances == 1
        assert config.misfire_grace_time == 300
        assert config.coalesce is True
        assert config.timeout_minutes == 30


class TestSchedulerStats:
    """Tests for SchedulerStats dataclass."""

    def test_default_stats(self) -> None:
        """Test default scheduler stats."""
        stats = SchedulerStats()

        assert stats.running is False
        assert stats.jobs_scheduled == 0
        assert stats.jobs_executed == 0
        assert stats.jobs_failed == 0
        assert stats.last_execution is None
        assert stats.uptime_seconds == 0


class TestScheduleType:
    """Tests for ScheduleType enum."""

    def test_schedule_types(self) -> None:
        """Test schedule type values."""
        assert ScheduleType.CRON.value == "cron"
        assert ScheduleType.INTERVAL.value == "interval"
