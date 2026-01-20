"""
Data validation transformations.

Handles:
- Data quality checks
- Schema validation
- Business rule validation
- Quality metrics calculation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

from etl_pipeline.exceptions import DataQualityError
from etl_pipeline.models import ExtractedRecord, TransformedRecord
from etl_pipeline.transformers.base import BaseTransformer


@dataclass
class ValidationResult:
    """Result of validating a single record."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class QualityMetrics:
    """Data quality metrics for a batch of records."""

    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    completeness_ratio: float = 0.0
    fields_completeness: dict[str, float] = field(default_factory=dict)

    @property
    def validity_ratio(self) -> float:
        """Ratio of valid to total records."""
        if self.total_records == 0:
            return 0.0
        return self.valid_records / self.total_records


class DataValidator(BaseTransformer):
    """
    Validates transformed records against quality rules.

    Validation rules:
    - Required fields must be present
    - Numeric values must be within expected ranges
    - Dates must be in valid ranges
    - Business rules (e.g., rating between 1-5)
    """

    def __init__(
        self,
        min_completeness: float = 0.8,
        fail_on_quality_error: bool = False,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize validator.

        Args:
            min_completeness: Minimum required completeness ratio (0-1)
            fail_on_quality_error: Whether to raise exception on quality issues
            config: Additional configuration
        """
        super().__init__(config)
        self.min_completeness = min_completeness
        self.fail_on_quality_error = fail_on_quality_error
        self.metrics: QualityMetrics | None = None

    @property
    def name(self) -> str:
        return "DataValidator"

    def transform(
        self, records: list[ExtractedRecord | TransformedRecord]
    ) -> list[TransformedRecord]:
        """Validate records and filter out invalid ones."""
        transformed = [r for r in records if isinstance(r, TransformedRecord)]

        valid_records: list[TransformedRecord] = []
        validation_errors: list[str] = []

        # Track completeness per field
        field_presence: dict[str, int] = {
            "title": 0,
            "description": 0,
            "url": 0,
            "category": 0,
            "numeric_value_1": 0,
            "numeric_value_2": 0,
        }

        for record in transformed:
            result = self._validate_record(record)

            if result.is_valid:
                valid_records.append(record)
            else:
                validation_errors.extend(result.errors)

            # Track field presence
            if record.title:
                field_presence["title"] += 1
            if record.description:
                field_presence["description"] += 1
            if record.url:
                field_presence["url"] += 1
            if record.category:
                field_presence["category"] += 1
            if record.numeric_value_1 is not None:
                field_presence["numeric_value_1"] += 1
            if record.numeric_value_2 is not None:
                field_presence["numeric_value_2"] += 1

        # Calculate metrics
        total = len(transformed)
        self.metrics = QualityMetrics(
            total_records=total,
            valid_records=len(valid_records),
            invalid_records=total - len(valid_records),
            completeness_ratio=len(valid_records) / total if total > 0 else 0.0,
            fields_completeness={
                field: count / total if total > 0 else 0.0
                for field, count in field_presence.items()
            },
        )

        self.logger.info(
            f"Validation complete: {self.metrics.valid_records}/{self.metrics.total_records} valid",
            extra={
                "validity_ratio": f"{self.metrics.validity_ratio:.2%}",
                "completeness": f"{self.metrics.completeness_ratio:.2%}",
            },
        )

        # Check quality threshold
        if self.metrics.completeness_ratio < self.min_completeness:
            message = (
                f"Data quality below threshold: {self.metrics.completeness_ratio:.2%} "
                f"< {self.min_completeness:.2%}"
            )
            self.logger.warning(message)

            if self.fail_on_quality_error:
                raise DataQualityError(
                    message,
                    metric="completeness",
                    expected=self.min_completeness,
                    actual=self.metrics.completeness_ratio,
                )

        return valid_records

    def _validate_record(self, record: TransformedRecord) -> ValidationResult:
        """Validate a single record."""
        errors: list[str] = []
        warnings: list[str] = []

        # Required fields
        if not record.source_id:
            errors.append("Missing source_id")
        if not record.title:
            errors.append("Missing title")

        # Title validation
        if record.title:
            if len(record.title) < 2:
                errors.append(f"Title too short: '{record.title}'")
            if len(record.title) > 500:
                warnings.append(f"Title very long: {len(record.title)} chars")

        # URL validation
        if record.url and not record.url.startswith(("http://", "https://")):
            warnings.append(f"Invalid URL scheme: {record.url}")

        # Numeric value validation (if present)
        if record.numeric_value_1 is not None:
            # For ratings (1-5) or stars (0+)
            if record.source.value == "sqlite" and not (0 <= record.numeric_value_1 <= 5):
                # Books have 1-5 rating
                warnings.append(f"Rating out of range: {record.numeric_value_1}")
            elif record.source.value == "github" and record.numeric_value_1 < 0:
                # Stars should be non-negative
                errors.append(f"Negative star count: {record.numeric_value_1}")

        # Date validation
        if record.source_created_at:
            from datetime import datetime

            now = datetime.now(UTC)

            # Make comparison timezone-aware
            source_date = record.source_created_at
            if source_date.tzinfo is None:
                source_date = source_date.replace(tzinfo=UTC)

            # Check for future dates
            if source_date > now:
                warnings.append("Source created date is in the future")

            # Check for very old dates (before 1990)
            if source_date.year < 1990:
                warnings.append(f"Very old source date: {source_date.year}")

        # Log warnings
        for warning in warnings:
            self.logger.debug(f"Validation warning for {record.source_identifier}: {warning}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def get_quality_report(self) -> dict[str, Any]:
        """Get detailed quality report."""
        if not self.metrics:
            return {"error": "No validation has been performed"}

        return {
            "summary": {
                "total_records": self.metrics.total_records,
                "valid_records": self.metrics.valid_records,
                "invalid_records": self.metrics.invalid_records,
                "validity_ratio": f"{self.metrics.validity_ratio:.2%}",
            },
            "completeness": {
                "overall": f"{self.metrics.completeness_ratio:.2%}",
                "by_field": {
                    field: f"{ratio:.2%}"
                    for field, ratio in self.metrics.fields_completeness.items()
                },
            },
            "thresholds": {
                "min_completeness": f"{self.min_completeness:.2%}",
                "passed": self.metrics.completeness_ratio >= self.min_completeness,
            },
        }
