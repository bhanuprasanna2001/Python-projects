"""
Tests for data models.

These tests verify:
1. Models validate data correctly
2. Computed properties work as expected
3. Model serialization/deserialization works
"""

from datetime import UTC, datetime
from uuid import UUID

from etl_pipeline.models import (
    DataSource,
    ExtractionResult,
    JobStatus,
    PipelineJob,
    Stage,
    StageResult,
    TransformedRecord,
)


class TestTransformedRecord:
    """Tests for TransformedRecord model."""

    def test_source_identifier_computation(self):
        """source_identifier should combine source and source_id."""
        record = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="12345",
            title="Test",
            extracted_at=datetime.now(UTC),
        )

        assert record.source_identifier == "github:12345"

    def test_generates_unique_id(self):
        """Each record should have a unique UUID."""
        record1 = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="1",
            title="Test 1",
            extracted_at=datetime.now(UTC),
        )
        record2 = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="2",
            title="Test 2",
            extracted_at=datetime.now(UTC),
        )

        assert isinstance(record1.id, UUID)
        assert record1.id != record2.id

    def test_defaults_transformed_at_to_now(self):
        """transformed_at should default to current time."""
        before = datetime.now(UTC)
        record = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="1",
            title="Test",
            extracted_at=before,
        )
        after = datetime.now(UTC)

        assert before <= record.transformed_at.replace(tzinfo=UTC) <= after


class TestExtractionResult:
    """Tests for ExtractionResult model."""

    def test_success_requires_completion_and_no_errors(self):
        """success should be True only when completed without errors."""
        result = ExtractionResult(source=DataSource.GITHUB)

        # Not complete yet
        assert not result.success

        # Complete it
        result.complete()
        assert result.success

        # Add errors
        result.error_count = 1
        assert not result.success

    def test_duration_calculation(self):
        """Should calculate duration when completed."""
        result = ExtractionResult(source=DataSource.GITHUB)

        assert result.duration_seconds is None

        result.complete()

        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0


class TestPipelineJob:
    """Tests for PipelineJob model."""

    def test_start_sets_status_and_time(self):
        """start() should set status to RUNNING and record time."""
        job = PipelineJob(pipeline_name="test")

        assert job.status == JobStatus.PENDING

        job.start()

        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_complete_sets_status_and_time(self):
        """complete() should set status and completion time."""
        job = PipelineJob(pipeline_name="test")
        job.start()

        job.complete(JobStatus.COMPLETED)

        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None

    def test_add_stage_result_tracks_errors(self):
        """Adding failed stage should increment error count."""
        job = PipelineJob(pipeline_name="test")

        job.add_stage_result(
            StageResult(
                stage=Stage.EXTRACT,
                status=JobStatus.FAILED,
                started_at=datetime.now(UTC),
            )
        )

        assert job.error_count == 1
        assert len(job.stages) == 1


class TestStageResult:
    """Tests for StageResult model."""

    def test_stores_metrics(self):
        """Should store arbitrary metrics."""
        result = StageResult(
            stage=Stage.EXTRACT,
            status=JobStatus.COMPLETED,
            started_at=datetime.now(UTC),
            metrics={"records_processed": 100, "errors": 0},
        )

        assert result.metrics["records_processed"] == 100
