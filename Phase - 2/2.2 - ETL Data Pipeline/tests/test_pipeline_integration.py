"""
Integration tests for the complete ETL pipeline.

These tests verify:
1. End-to-end pipeline execution works
2. All stages communicate correctly
3. Error handling propagates appropriately
4. Pipeline produces expected output
"""

from pathlib import Path

import pytest

from etl_pipeline.config import Settings
from etl_pipeline.models import DataSource, JobStatus, Stage
from etl_pipeline.orchestration.pipeline import Pipeline


class TestPipelineIntegration:
    """Integration tests for the full pipeline."""

    @pytest.fixture
    def pipeline_with_local_sources(
        self, tmp_data_dir: Path, sample_csv_file: Path, sample_sqlite_db: Path
    ) -> Pipeline:
        """Create pipeline configured with local test data sources."""
        settings = Settings(
            log_level="DEBUG",
            pipeline={"name": "integration-test"},
            sources={
                "github": {"enabled": False},  # Skip API calls in tests
                "weather": {"enabled": True, "path": str(sample_csv_file)},
                "books": {"enabled": True, "fallback_path": str(sample_sqlite_db)},
            },
            loading={
                "target": "sqlite",
                "sqlite": {"path": str(tmp_data_dir / "output.db")},
            },
            transformations={
                "handle_missing": "fill_default",
                "deduplicate": True,
                "quality": {"min_completeness": 0.5},
            },
        )
        return Pipeline(settings)

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, pipeline_with_local_sources: Pipeline):
        """Should execute all ETL stages successfully."""
        job = await pipeline_with_local_sources.run()

        assert job.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]
        assert job.total_extracted > 0
        assert job.total_transformed > 0
        assert job.total_loaded > 0

    @pytest.mark.asyncio
    async def test_extraction_only(self, pipeline_with_local_sources: Pipeline):
        """Should run extraction stage only."""
        job = await pipeline_with_local_sources.run(stages=[Stage.EXTRACT])

        # PARTIAL is expected when some extractors succeed but others fail
        # (e.g., SQLite extractor may fail if DB doesn't exist in test env)
        assert job.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]
        assert job.total_extracted > 0
        # Transform and load not run
        assert job.total_transformed == 0
        assert job.total_loaded == 0
        assert len(job.stages) == 1
        assert job.stages[0].stage == Stage.EXTRACT

    @pytest.mark.asyncio
    async def test_pipeline_tracks_stage_metrics(self, pipeline_with_local_sources: Pipeline):
        """Should record metrics for each pipeline stage."""
        job = await pipeline_with_local_sources.run()

        # Should have results for all 3 stages
        assert len(job.stages) == 3

        # Check extraction stage
        extract_stage = next(s for s in job.stages if s.stage == Stage.EXTRACT)
        assert extract_stage.record_count > 0
        assert "total_records" in extract_stage.metrics

        # Check transformation stage
        transform_stage = next(s for s in job.stages if s.stage == Stage.TRANSFORM)
        assert transform_stage.record_count > 0

        # Check loading stage
        load_stage = next(s for s in job.stages if s.stage == Stage.LOAD)
        assert "records_inserted" in load_stage.metrics

    @pytest.mark.asyncio
    async def test_pipeline_status_after_run(self, pipeline_with_local_sources: Pipeline):
        """Should provide accurate status information."""
        await pipeline_with_local_sources.run()

        status = await pipeline_with_local_sources.get_status()

        assert status["pipeline_name"] == "integration-test"
        assert status["sources"]["configured"] >= 1
        assert status["database"]["total_records"] > 0

    @pytest.mark.asyncio
    async def test_pipeline_source_validation(self, pipeline_with_local_sources: Pipeline):
        """Should validate all configured sources."""
        results = await pipeline_with_local_sources.validate_sources()

        # At least one source should be valid
        assert any(results.values())

    @pytest.mark.asyncio
    async def test_idempotent_pipeline_runs(self, pipeline_with_local_sources: Pipeline):
        """Running pipeline twice should not duplicate data."""
        # First run
        job1 = await pipeline_with_local_sources.run()

        # Second run - should update, not duplicate
        job2 = await pipeline_with_local_sources.run()

        # Both should complete
        assert job1.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]
        assert job2.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]

        # Check database - should not have 2x records
        status = await pipeline_with_local_sources.get_status()
        # Second run should have updates, not inserts
        # (This validates the upsert logic works end-to-end)
        assert status["database"]["total_records"] == job1.total_loaded


class TestPipelineConfiguration:
    """Tests for pipeline configuration behavior."""

    def test_creates_default_extractors_from_config(self, sample_settings: Settings):
        """Should create extractors based on configuration."""
        pipeline = Pipeline(sample_settings)

        # GitHub disabled, so should have CSV and SQLite
        source_types = [e.source for e in pipeline.extractors]

        assert DataSource.CSV in source_types
        assert DataSource.SQLITE in source_types
        assert DataSource.GITHUB not in source_types

    def test_creates_loader_from_config(self, sample_settings: Settings):
        """Should create loader based on configuration."""
        pipeline = Pipeline(sample_settings)

        assert pipeline.loader is not None
        assert pipeline.loader.target_name == "sqlite"


class TestPipelineJobTracking:
    """Tests for pipeline job tracking."""

    @pytest.fixture
    def pipeline_with_local_sources(
        self, tmp_data_dir: Path, sample_csv_file: Path, sample_sqlite_db: Path
    ) -> Pipeline:
        """Create pipeline configured with local test data sources."""
        settings = Settings(
            log_level="DEBUG",
            pipeline={"name": "integration-test"},
            sources={
                "github": {"enabled": False},
                "weather": {"enabled": True, "path": str(sample_csv_file)},
                "books": {"enabled": True, "fallback_path": str(sample_sqlite_db)},
            },
            loading={
                "target": "sqlite",
                "sqlite": {"path": str(tmp_data_dir / "output.db")},
            },
            transformations={
                "handle_missing": "fill_default",
                "deduplicate": True,
                "quality": {"min_completeness": 0.5},
            },
        )
        return Pipeline(settings)

    @pytest.mark.asyncio
    async def test_job_has_unique_id(self, pipeline_with_local_sources: Pipeline):
        """Each pipeline run should have unique job ID."""
        job1 = await pipeline_with_local_sources.run()
        job2 = await pipeline_with_local_sources.run()

        assert job1.job_id != job2.job_id

    @pytest.mark.asyncio
    async def test_job_tracks_duration(self, pipeline_with_local_sources: Pipeline):
        """Job should track execution duration."""
        job = await pipeline_with_local_sources.run()

        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.duration_seconds > 0
        assert job.completed_at > job.started_at

    @pytest.mark.asyncio
    async def test_job_stores_config_snapshot(self, pipeline_with_local_sources: Pipeline):
        """Job should store configuration used for the run."""
        job = await pipeline_with_local_sources.run()

        assert "sources" in job.config_snapshot
        assert "stages" in job.config_snapshot
