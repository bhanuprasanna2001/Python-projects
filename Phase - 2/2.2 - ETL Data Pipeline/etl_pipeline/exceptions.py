"""
Custom exceptions for the ETL pipeline.

Exception hierarchy:
- ETLError (base)
  - ExtractionError
    - SourceConnectionError
    - RateLimitError
    - DataValidationError
  - TransformationError
    - SchemaError
    - DataQualityError
  - LoadingError
    - DatabaseConnectionError
    - IntegrityError
  - ConfigurationError
  - PipelineError
"""

from __future__ import annotations

from typing import Any


class ETLError(Exception):
    """
    Base exception for all ETL pipeline errors.

    Attributes:
        message: Human-readable error description
        details: Additional context for debugging
        recoverable: Whether the error might be resolved by retry
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }


# --- Extraction Errors ---


class ExtractionError(ETLError):
    """Base exception for extraction stage errors."""

    def __init__(
        self,
        message: str,
        source: str | None = None,
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        details = details or {}
        if source:
            details["source"] = source
        super().__init__(message, details, recoverable)
        self.source = source


class SourceConnectionError(ExtractionError):
    """Failed to connect to data source."""

    def __init__(
        self,
        source: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"Failed to connect to source '{source}': {reason}"
        super().__init__(message, source, details, recoverable=True)


class RateLimitError(ExtractionError):
    """Rate limit exceeded for data source."""

    def __init__(
        self,
        source: str,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        message = f"Rate limit exceeded for source '{source}'"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(message, source, details, recoverable=True)
        self.retry_after = retry_after


class DataValidationError(ExtractionError):
    """Extracted data failed validation."""

    def __init__(
        self,
        source: str,
        validation_errors: list[str],
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["validation_errors"] = validation_errors
        message = f"Data validation failed for source '{source}': {len(validation_errors)} error(s)"
        super().__init__(message, source, details, recoverable=False)
        self.validation_errors = validation_errors


# --- Transformation Errors ---


class TransformationError(ETLError):
    """Base exception for transformation stage errors."""

    def __init__(
        self,
        message: str,
        stage: str | None = None,
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        details = details or {}
        if stage:
            details["transformation_stage"] = stage
        super().__init__(message, details, recoverable)
        self.stage = stage


class SchemaError(TransformationError):
    """Schema mismatch or invalid schema."""

    def __init__(
        self,
        message: str,
        expected_schema: dict[str, Any] | None = None,
        actual_schema: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if expected_schema:
            details["expected_schema"] = expected_schema
        if actual_schema:
            details["actual_schema"] = actual_schema
        super().__init__(message, stage="schema_validation", details=details)


class DataQualityError(TransformationError):
    """Data quality thresholds not met."""

    def __init__(
        self,
        message: str,
        metric: str,
        expected: float,
        actual: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["quality_metric"] = metric
        details["expected_value"] = expected
        details["actual_value"] = actual
        super().__init__(message, stage="quality_check", details=details)
        self.metric = metric
        self.expected = expected
        self.actual = actual


# --- Loading Errors ---


class LoadingError(ETLError):
    """Base exception for loading stage errors."""

    def __init__(
        self,
        message: str,
        target: str | None = None,
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        details = details or {}
        if target:
            details["target"] = target
        super().__init__(message, details, recoverable)
        self.target = target


class DatabaseConnectionError(LoadingError):
    """Failed to connect to target database."""

    def __init__(
        self,
        target: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"Failed to connect to database '{target}': {reason}"
        super().__init__(message, target, details, recoverable=True)


class IntegrityError(LoadingError):
    """Database integrity constraint violated."""

    def __init__(
        self,
        target: str,
        constraint: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        details["constraint"] = constraint
        message = f"Integrity constraint '{constraint}' violated in '{target}'"
        super().__init__(message, target, details, recoverable=False)
        self.constraint = constraint


# --- Configuration Errors ---


class ConfigurationError(ETLError):
    """Invalid or missing configuration."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details, recoverable=False)
        self.config_key = config_key


# --- Pipeline Errors ---


class PipelineError(ETLError):
    """Pipeline orchestration error."""

    def __init__(
        self,
        message: str,
        stage: str | None = None,
        job_id: str | None = None,
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        details = details or {}
        if stage:
            details["stage"] = stage
        if job_id:
            details["job_id"] = job_id
        super().__init__(message, details, recoverable)
        self.stage = stage
        self.job_id = job_id
