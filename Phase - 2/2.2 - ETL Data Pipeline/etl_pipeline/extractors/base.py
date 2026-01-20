"""
Base extractor interface.

All extractors inherit from this abstract class, ensuring consistent
behavior and enabling polymorphic usage in the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar

from etl_pipeline.exceptions import ExtractionError
from etl_pipeline.models import DataSource, ExtractedRecord, ExtractionResult
from etl_pipeline.utils.logging import get_logger

T = TypeVar("T", bound=ExtractedRecord)


class BaseExtractor(ABC, Generic[T]):
    """
    Abstract base class for all data extractors.

    Each extractor is responsible for:
    1. Connecting to a data source
    2. Fetching raw data
    3. Converting to ExtractedRecord instances
    4. Tracking extraction metrics

    Type parameter T is the specific ExtractedRecord subclass this extractor produces.
    """

    def __init__(self, source: DataSource, config: dict[str, Any] | None = None) -> None:
        """
        Initialize the extractor.

        Args:
            source: The data source type
            config: Source-specific configuration
        """
        self.source = source
        self.config = config or {}
        self.logger = get_logger(f"extractor.{source.value}", source=source.value)

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this extractor."""
        ...

    @abstractmethod
    async def extract(self) -> ExtractionResult:
        """
        Extract data from the source.

        Returns:
            ExtractionResult containing records and metadata

        Raises:
            ExtractionError: If extraction fails
        """
        ...

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the data source is accessible.

        Returns:
            True if connection is valid, False otherwise
        """
        ...

    def _create_result(self) -> ExtractionResult:
        """Create an empty ExtractionResult for this source."""
        return ExtractionResult(
            source=self.source,
            started_at=datetime.utcnow(),
        )

    def _handle_error(self, result: ExtractionResult, error: Exception) -> None:
        """
        Record an error in the extraction result.

        Args:
            result: The ExtractionResult to update
            error: The exception that occurred
        """
        result.error_count += 1
        result.errors.append(str(error))
        self.logger.error(
            f"Extraction error: {error}",
            extra={"error_type": type(error).__name__},
            exc_info=True,
        )

    async def __aenter__(self) -> BaseExtractor[T]:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - override for cleanup."""
        pass


class SyncExtractor(BaseExtractor[T]):
    """
    Base class for synchronous extractors.

    Wraps sync extraction logic in async interface for pipeline compatibility.
    """

    @abstractmethod
    def _extract_sync(self) -> list[T]:
        """
        Synchronous extraction implementation.

        Returns:
            List of extracted records
        """
        ...

    @abstractmethod
    def _validate_connection_sync(self) -> bool:
        """Synchronous connection validation."""
        ...

    async def extract(self) -> ExtractionResult:
        """Wrap sync extraction in async interface."""
        result = self._create_result()

        try:
            self.logger.info(f"Starting extraction from {self.name}")
            records = self._extract_sync()
            result.records = records  # type: ignore[assignment]
            self.logger.info(f"Extracted {len(records)} records from {self.name}")
        except Exception as e:
            self._handle_error(result, e)
            if not isinstance(e, ExtractionError):
                raise ExtractionError(
                    f"Extraction failed for {self.name}: {e}",
                    source=self.source.value,
                    recoverable=True,
                ) from e
            raise
        finally:
            result.complete()

        return result

    async def validate_connection(self) -> bool:
        """Wrap sync validation in async interface."""
        return self._validate_connection_sync()
