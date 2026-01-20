"""
Base loader interface.

All loaders inherit from this abstract class, ensuring consistent
behavior for loading data to various targets.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from etl_pipeline.models import LoadingResult, TransformedRecord
from etl_pipeline.utils.logging import get_logger


class BaseLoader(ABC):
    """
    Abstract base class for all data loaders.

    Each loader is responsible for:
    1. Connecting to a target (database, file, API)
    2. Creating/managing schema
    3. Loading records with upsert logic
    4. Tracking loading metrics
    """

    def __init__(
        self,
        target_name: str,
        on_conflict: Literal["skip", "update", "fail"] = "update",
        batch_size: int = 1000,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize loader.

        Args:
            target_name: Human-readable name for the target
            on_conflict: How to handle duplicate records
            batch_size: Number of records to load per batch
            config: Target-specific configuration
        """
        self.target_name = target_name
        self.on_conflict = on_conflict
        self.batch_size = batch_size
        self.config = config or {}
        self.logger = get_logger(f"loader.{target_name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this loader."""
        ...

    @abstractmethod
    async def load(self, records: list[TransformedRecord]) -> LoadingResult:
        """
        Load records to the target.

        Args:
            records: Transformed records to load

        Returns:
            LoadingResult with metrics

        Raises:
            LoadingError: If loading fails
        """
        ...

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the target is accessible and writable.

        Returns:
            True if connection is valid
        """
        ...

    @abstractmethod
    async def initialize_schema(self) -> None:
        """
        Create or update schema in the target.

        Should be idempotent (safe to call multiple times).
        """
        ...

    def _create_result(self) -> LoadingResult:
        """Create an empty LoadingResult for this target."""
        return LoadingResult(
            target=self.target_name,
            started_at=datetime.utcnow(),
        )

    def _handle_error(self, result: LoadingResult, error: Exception) -> None:
        """Record an error in the loading result."""
        result.records_failed += 1
        result.errors.append(str(error))
        self.logger.error(
            f"Loading error: {error}",
            extra={"error_type": type(error).__name__},
            exc_info=True,
        )

    async def __aenter__(self) -> BaseLoader:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - override for cleanup."""
        pass
