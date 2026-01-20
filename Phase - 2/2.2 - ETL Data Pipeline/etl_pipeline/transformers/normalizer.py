"""
Data normalization transformations.

Handles:
- Schema unification
- Date/time normalization
- Text normalization
- Deduplication
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from etl_pipeline.models import ExtractedRecord, TransformedRecord
from etl_pipeline.transformers.base import BaseTransformer


class DataNormalizer(BaseTransformer):
    """
    Normalizes transformed records to ensure consistency.

    Operations:
    - Normalize timestamps to UTC
    - Standardize text fields (trim, lowercase tags)
    - Remove duplicates based on source_identifier
    - Ensure consistent data types
    """

    def __init__(
        self,
        deduplicate: bool = True,
        normalize_dates: bool = True,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize normalizer.

        Args:
            deduplicate: Whether to remove duplicate records
            normalize_dates: Whether to normalize dates to UTC
            config: Additional configuration
        """
        super().__init__(config)
        self.deduplicate = deduplicate
        self.normalize_dates = normalize_dates

    @property
    def name(self) -> str:
        return "DataNormalizer"

    def transform(
        self, records: list[ExtractedRecord | TransformedRecord]
    ) -> list[TransformedRecord]:
        """Normalize records."""
        # Filter to only TransformedRecords (cleaners should have converted)
        transformed = [r for r in records if isinstance(r, TransformedRecord)]

        # Normalize each record
        normalized = [self._normalize_record(r) for r in transformed]

        # Deduplicate if enabled
        if self.deduplicate:
            normalized = self._deduplicate(normalized)

        return normalized

    def _normalize_record(self, record: TransformedRecord) -> TransformedRecord:
        """Normalize a single record."""
        # Normalize timestamps to UTC
        if self.normalize_dates:
            record.source_created_at = self._normalize_datetime(record.source_created_at)
            record.source_updated_at = self._normalize_datetime(record.source_updated_at)
            record.extracted_at = self._normalize_datetime(record.extracted_at) or datetime.now(UTC)
            record.transformed_at = datetime.now(UTC)

        # Normalize title
        if record.title:
            record.title = record.title.strip()

        # Normalize description
        if record.description:
            record.description = record.description.strip()
            # Remove excessive whitespace
            import re

            record.description = re.sub(r"\s+", " ", record.description)

        # Normalize tags (lowercase, deduplicate)
        if record.tags:
            record.tags = list(dict.fromkeys(tag.lower().strip() for tag in record.tags if tag))

        # Normalize URL
        if record.url:
            record.url = record.url.strip()

        # Normalize category
        if record.category:
            record.category = record.category.strip().title()

        return record

    def _normalize_datetime(self, dt: datetime | None) -> datetime | None:
        """Normalize datetime to UTC."""
        if dt is None:
            return None

        # If naive datetime, assume UTC
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)

        # Convert to UTC
        return dt.astimezone(UTC)

    def _deduplicate(self, records: list[TransformedRecord]) -> list[TransformedRecord]:
        """
        Remove duplicate records based on source_identifier.

        Keeps the most recently extracted version.
        """
        seen: dict[str, TransformedRecord] = {}
        duplicates = 0

        for record in records:
            key = record.source_identifier

            if key in seen:
                duplicates += 1
                # Keep the more recent one
                existing = seen[key]
                if record.extracted_at > existing.extracted_at:
                    seen[key] = record
            else:
                seen[key] = record

        if duplicates > 0:
            self.logger.info(
                f"Removed {duplicates} duplicate records",
                extra={"duplicates_removed": duplicates},
            )

        return list(seen.values())
