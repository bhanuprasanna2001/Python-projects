"""
Data models for the ETL pipeline.

This module defines the data contracts at each stage:
- Extracted: Raw data from sources (source-specific models)
- Transformed: Normalized, cleaned data (unified schema)
- Job: Pipeline execution metadata
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

# --- Enums ---


class DataSource(str, Enum):
    """Supported data sources."""

    GITHUB = "github"
    CSV = "csv"
    SQLITE = "sqlite"


class JobStatus(str, Enum):
    """Pipeline job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some stages succeeded, some failed


class Stage(str, Enum):
    """Pipeline stages."""

    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"


# --- Extracted Data Models (Source-Specific) ---


class ExtractedRecord(BaseModel):
    """
    Base model for extracted records.

    All extracted data includes metadata about its source and extraction time.
    """

    source: DataSource
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}


class GitHubRepository(ExtractedRecord):
    """GitHub repository data from API."""

    source: DataSource = DataSource.GITHUB
    repo_id: int
    name: str
    full_name: str
    description: str | None = None
    html_url: str
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    topics: list[str] = Field(default_factory=list)
    owner_login: str = ""


class WeatherRecord(ExtractedRecord):
    """Weather data from CSV files."""

    source: DataSource = DataSource.CSV
    date: datetime
    location: str
    temperature_celsius: float | None = None
    humidity_percent: float | None = None
    precipitation_mm: float | None = None
    wind_speed_kmh: float | None = None
    conditions: str | None = None


class BookRecord(ExtractedRecord):
    """Book data from SQLite database (web scraper output)."""

    source: DataSource = DataSource.SQLITE
    title: str
    price: float | None = None
    rating: int | None = None  # 1-5 stars
    availability: str | None = None
    url: str | None = None
    upc: str | None = None  # Universal Product Code


# --- Transformed Data Models (Unified Schema) ---


class TransformedRecord(BaseModel):
    """
    Unified record after transformation.

    All data sources are normalized to this common schema for loading.
    This enables cross-source analysis and consistent storage.
    """

    id: UUID = Field(default_factory=uuid4)
    source: DataSource
    source_id: str  # Original ID from source (repo_id, book upc, etc.)

    # Common fields
    title: str
    description: str | None = None
    url: str | None = None
    category: str | None = None

    # Metrics (nullable, not all sources have these)
    numeric_value_1: float | None = None  # stars/rating/temperature
    numeric_value_2: float | None = None  # forks/price/humidity

    # Timestamps
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None
    extracted_at: datetime
    transformed_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    tags: list[str] = Field(default_factory=list)
    extra_data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @computed_field
    @property
    def source_identifier(self) -> str:
        """Unique identifier combining source and source_id."""
        return f"{self.source.value}:{self.source_id}"


# --- Extraction Result Container ---


class ExtractionResult(BaseModel):
    """
    Result of an extraction operation.

    Contains extracted records plus metadata about the extraction.
    """

    source: DataSource
    records: list[ExtractedRecord] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    record_count: int = 0
    error_count: int = 0
    errors: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def success(self) -> bool:
        """Whether extraction completed without errors."""
        return self.error_count == 0 and self.completed_at is not None

    @computed_field
    @property
    def duration_seconds(self) -> float | None:
        """Duration of extraction in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def complete(self) -> None:
        """Mark extraction as complete."""
        self.completed_at = datetime.utcnow()
        self.record_count = len(self.records)


# --- Transformation Result Container ---


class TransformationResult(BaseModel):
    """
    Result of a transformation operation.

    Contains transformed records plus quality metrics.
    """

    records: list[TransformedRecord] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Metrics
    input_count: int = 0
    output_count: int = 0
    dropped_count: int = 0
    duplicate_count: int = 0
    validation_errors: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def success(self) -> bool:
        """Whether transformation completed."""
        return self.completed_at is not None

    @computed_field
    @property
    def completeness_ratio(self) -> float:
        """Ratio of output to input records."""
        if self.input_count == 0:
            return 0.0
        return self.output_count / self.input_count

    def complete(self) -> None:
        """Mark transformation as complete."""
        self.completed_at = datetime.utcnow()
        self.output_count = len(self.records)


# --- Loading Result Container ---


class LoadingResult(BaseModel):
    """
    Result of a loading operation.

    Contains statistics about the load operation.
    """

    target: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Metrics
    records_attempted: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    errors: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def success(self) -> bool:
        """Whether loading completed without critical errors."""
        return self.completed_at is not None and self.records_failed == 0

    @computed_field
    @property
    def total_processed(self) -> int:
        """Total records successfully processed."""
        return self.records_inserted + self.records_updated + self.records_skipped

    def complete(self) -> None:
        """Mark loading as complete."""
        self.completed_at = datetime.utcnow()


# --- Pipeline Job Model ---


class StageResult(BaseModel):
    """Result of a single pipeline stage."""

    stage: Stage
    status: JobStatus
    started_at: datetime
    completed_at: datetime | None = None
    record_count: int = 0
    error_message: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class PipelineJob(BaseModel):
    """
    Complete pipeline job execution record.

    Tracks the entire ETL run from start to finish.
    """

    job_id: UUID = Field(default_factory=uuid4)
    pipeline_name: str
    status: JobStatus = JobStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Stage results
    stages: list[StageResult] = Field(default_factory=list)

    # Summary metrics
    total_extracted: int = 0
    total_transformed: int = 0
    total_loaded: int = 0
    error_count: int = 0

    # Configuration snapshot
    config_snapshot: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def duration_seconds(self) -> float | None:
        """Total job duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def start(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, status: JobStatus = JobStatus.COMPLETED) -> None:
        """Mark job as completed."""
        self.status = status
        self.completed_at = datetime.utcnow()

    def add_stage_result(self, result: StageResult) -> None:
        """Add a stage result to the job."""
        self.stages.append(result)
        if result.status == JobStatus.FAILED:
            self.error_count += 1
