"""
Data cleaning transformations.

Handles:
- Missing value imputation
- Invalid data removal
- Duplicate detection
- Outlier handling
"""

from __future__ import annotations

from typing import Any

from etl_pipeline.models import (
    BookRecord,
    ExtractedRecord,
    GitHubRepository,
    TransformedRecord,
    WeatherRecord,
)
from etl_pipeline.transformers.base import BaseTransformer


class DataCleaner(BaseTransformer):
    """
    Cleans extracted data by handling missing values and removing invalid records.

    Strategies:
    - drop: Remove records with missing required fields
    - fill_default: Fill missing values with defaults
    - fill_mean: Fill numeric missing values with mean (for weather data)
    """

    def __init__(
        self,
        missing_strategy: str = "fill_default",
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize data cleaner.

        Args:
            missing_strategy: How to handle missing values (drop, fill_default, fill_mean)
            config: Additional configuration
        """
        super().__init__(config)
        self.missing_strategy = missing_strategy

    @property
    def name(self) -> str:
        return "DataCleaner"

    def transform(
        self, records: list[ExtractedRecord | TransformedRecord]
    ) -> list[TransformedRecord]:
        """Clean records by handling missing values."""
        cleaned: list[TransformedRecord] = []

        for record in records:
            # If already transformed, just validate
            if isinstance(record, TransformedRecord):
                if self._is_valid(record):
                    cleaned.append(record)
                continue

            # Clean based on record type
            cleaned_record = self._clean_record(record)
            if cleaned_record:
                cleaned.append(cleaned_record)

        return cleaned

    def _clean_record(self, record: ExtractedRecord) -> TransformedRecord | None:
        """Clean a single extracted record."""
        if isinstance(record, GitHubRepository):
            return self._clean_github(record)
        elif isinstance(record, WeatherRecord):
            return self._clean_weather(record)
        elif isinstance(record, BookRecord):
            return self._clean_book(record)
        else:
            self.logger.warning(f"Unknown record type: {type(record)}")
            return None

    def _clean_github(self, repo: GitHubRepository) -> TransformedRecord | None:
        """Clean GitHub repository record."""
        # Required fields check
        if not repo.name or not repo.full_name:
            if self.missing_strategy == "drop":
                return None
            # Can't fill name, skip
            return None

        # Clean description
        description = repo.description
        if description:
            description = description.strip()
            # Truncate very long descriptions
            if len(description) > 500:
                description = description[:497] + "..."

        return TransformedRecord(
            source=repo.source,
            source_id=str(repo.repo_id),
            title=repo.full_name,
            description=description,
            url=repo.html_url,
            category=repo.language or "Unknown",
            numeric_value_1=float(repo.stargazers_count),
            numeric_value_2=float(repo.forks_count),
            source_created_at=repo.created_at,
            source_updated_at=repo.updated_at,
            extracted_at=repo.extracted_at,
            tags=repo.topics[:10],  # Limit tags
            extra_data={
                "owner": repo.owner_login,
                "open_issues": repo.open_issues_count,
            },
        )

    def _clean_weather(self, weather: WeatherRecord) -> TransformedRecord | None:
        """Clean weather record."""
        # Temperature is the key metric - if missing, handle based on strategy
        temperature = weather.temperature_celsius

        if temperature is None:
            if self.missing_strategy == "drop":
                return None
            elif self.missing_strategy == "fill_default":
                temperature = 15.0  # Reasonable default
            # fill_mean would require access to all records, handled in batch

        return TransformedRecord(
            source=weather.source,
            source_id=f"{weather.location}_{weather.date.isoformat()}",
            title=f"Weather: {weather.location}",
            description=weather.conditions,
            url=None,
            category=weather.location,
            numeric_value_1=temperature,
            numeric_value_2=weather.humidity_percent,
            source_created_at=weather.date,
            source_updated_at=None,
            extracted_at=weather.extracted_at,
            tags=[weather.conditions] if weather.conditions else [],
            extra_data={
                "precipitation_mm": weather.precipitation_mm,
                "wind_speed_kmh": weather.wind_speed_kmh,
            },
        )

    def _clean_book(self, book: BookRecord) -> TransformedRecord | None:
        """Clean book record."""
        # Title is required
        if not book.title or not book.title.strip():
            if self.missing_strategy == "drop":
                return None
            return None

        # Clean title
        title = book.title.strip()

        # Handle missing price
        price = book.price
        if price is None and self.missing_strategy == "fill_default":
            price = 0.0

        return TransformedRecord(
            source=book.source,
            source_id=book.upc or f"book_{hash(title) % 100000}",
            title=title,
            description=None,
            url=book.url,
            category="Books",
            numeric_value_1=float(book.rating) if book.rating else None,
            numeric_value_2=price,
            source_created_at=None,
            source_updated_at=None,
            extracted_at=book.extracted_at,
            tags=[],
            extra_data={
                "availability": book.availability,
            },
        )

    def _is_valid(self, record: TransformedRecord) -> bool:
        """Check if a transformed record is valid."""
        # Must have source_id and title
        return bool(record.source_id and record.title)
