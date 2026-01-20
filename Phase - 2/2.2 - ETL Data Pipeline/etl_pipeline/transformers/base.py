"""
Base transformer interface.

Transformers follow the Chain of Responsibility pattern, allowing
multiple transformations to be composed together.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from etl_pipeline.exceptions import TransformationError
from etl_pipeline.models import (
    ExtractedRecord,
    TransformationResult,
    TransformedRecord,
)
from etl_pipeline.utils.logging import get_logger


class BaseTransformer(ABC):
    """
    Abstract base class for data transformers.

    Each transformer performs a specific transformation:
    - Cleaning (remove invalid data)
    - Normalizing (convert to unified schema)
    - Validating (check data quality)
    - Enriching (add derived fields)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize transformer.

        Args:
            config: Transformation-specific configuration
        """
        self.config = config or {}
        self.logger = get_logger(f"transformer.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this transformer."""
        ...

    @abstractmethod
    def transform(
        self, records: list[ExtractedRecord | TransformedRecord]
    ) -> list[TransformedRecord]:
        """
        Transform a batch of records.

        Args:
            records: Input records (extracted or partially transformed)

        Returns:
            List of transformed records

        Raises:
            TransformationError: If transformation fails critically
        """
        ...


class TransformerChain:
    """
    Chains multiple transformers together.

    Executes transformers in sequence, passing output of each
    to the next. Collects metrics from each stage.

    Example:
        chain = TransformerChain([
            DataCleaner(),
            DataNormalizer(),
            DataValidator(),
        ])
        result = chain.execute(extracted_records)
    """

    def __init__(self, transformers: list[BaseTransformer]) -> None:
        """
        Initialize transformer chain.

        Args:
            transformers: List of transformers to execute in order
        """
        self.transformers = transformers
        self.logger = get_logger("transformer.chain")

    def execute(self, records: list[ExtractedRecord]) -> TransformationResult:
        """
        Execute all transformers in sequence.

        Args:
            records: Extracted records to transform

        Returns:
            TransformationResult with transformed records and metrics
        """
        result = TransformationResult(
            started_at=datetime.utcnow(),
            input_count=len(records),
        )

        current_records: list[Any] = list(records)

        self.logger.info(
            f"Starting transformation chain with {len(records)} records",
            extra={"transformers": [t.name for t in self.transformers]},
        )

        for transformer in self.transformers:
            try:
                before_count = len(current_records)
                current_records = transformer.transform(current_records)
                after_count = len(current_records)

                if before_count != after_count:
                    result.dropped_count += before_count - after_count
                    self.logger.info(
                        f"{transformer.name}: {before_count} → {after_count} records",
                        extra={
                            "transformer": transformer.name,
                            "dropped": before_count - after_count,
                        },
                    )

            except TransformationError:
                raise
            except Exception as e:
                self.logger.error(
                    f"Transformer '{transformer.name}' failed: {e}",
                    exc_info=True,
                )
                raise TransformationError(
                    f"Transformation failed at {transformer.name}: {e}",
                    stage=transformer.name,
                    recoverable=False,
                ) from e

        # Ensure all records are TransformedRecord at the end
        result.records = [r for r in current_records if isinstance(r, TransformedRecord)]
        result.complete()

        self.logger.info(
            f"Transformation complete: {result.input_count} → {result.output_count} records",
            extra={
                "input": result.input_count,
                "output": result.output_count,
                "dropped": result.dropped_count,
            },
        )

        return result
