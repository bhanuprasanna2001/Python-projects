"""
CSV file extractor.

Extracts data from CSV files with:
- Schema detection
- Type inference
- Missing value handling
- Support for local files and URLs
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from etl_pipeline.config import get_project_root
from etl_pipeline.exceptions import ExtractionError, SourceConnectionError
from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.models import DataSource, ExtractionResult, WeatherRecord


class CSVExtractor(BaseExtractor[WeatherRecord]):
    """
    Extracts data from CSV files.

    Uses Polars for efficient CSV parsing with automatic type inference.
    Supports both local files and HTTP URLs.
    """

    def __init__(
        self,
        file_path: str | Path,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize CSV extractor.

        Args:
            file_path: Path to CSV file (local or URL)
            config: Additional configuration (delimiter, encoding, etc.)
        """
        super().__init__(DataSource.CSV, config)
        self.file_path = Path(file_path) if not str(file_path).startswith("http") else file_path
        self._resolved_path: Path | None = None

    @property
    def name(self) -> str:
        return f"CSV ({self.file_path})"

    def _resolve_path(self) -> Path:
        """Resolve relative paths to absolute."""
        if self._resolved_path:
            return self._resolved_path

        if isinstance(self.file_path, str) and self.file_path.startswith("http"):
            raise ValueError("URL paths don't need resolution")

        path = Path(self.file_path)
        if not path.is_absolute():
            path = get_project_root() / path

        self._resolved_path = path
        return path

    async def validate_connection(self) -> bool:
        """Check if CSV file exists and is readable."""
        try:
            if isinstance(self.file_path, str) and self.file_path.startswith("http"):
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.head(str(self.file_path))
                    return response.status_code == 200
            else:
                path = self._resolve_path()
                return path.exists() and path.is_file()
        except Exception as e:
            self.logger.warning(f"CSV validation failed: {e}")
            return False

    def _parse_row_to_weather(self, row: dict[str, Any], row_index: int) -> WeatherRecord | None:
        """
        Parse a CSV row into a WeatherRecord.

        Handles various column naming conventions and missing values.
        """
        try:
            # Try to extract date - common column names
            date_value = None
            for col in ["date", "Date", "DATE", "timestamp", "Timestamp", "time"]:
                if col in row and row[col] is not None:
                    date_value = row[col]
                    break

            if date_value is None:
                self.logger.warning(f"Row {row_index}: Missing date field")
                return None

            # Parse date
            if isinstance(date_value, datetime):
                date = date_value
            elif isinstance(date_value, str):
                # Try common date formats
                for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        date = datetime.strptime(date_value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    self.logger.warning(f"Row {row_index}: Unparseable date '{date_value}'")
                    return None
            else:
                date = datetime.utcnow()

            # Extract location
            location = None
            for col in ["location", "Location", "city", "City", "station", "Station"]:
                if col in row and row[col] is not None:
                    location = str(row[col])
                    break
            location = location or "Unknown"

            # Extract numeric values with flexible column names
            def get_float(columns: list[str]) -> float | None:
                for col in columns:
                    if col in row and row[col] is not None:
                        try:
                            return float(row[col])
                        except (ValueError, TypeError):
                            pass
                return None

            return WeatherRecord(
                date=date,
                location=location,
                temperature_celsius=get_float(
                    ["temperature", "temp", "Temperature", "temp_c", "temperature_celsius"]
                ),
                humidity_percent=get_float(
                    ["humidity", "Humidity", "humidity_percent", "relative_humidity"]
                ),
                precipitation_mm=get_float(
                    ["precipitation", "precip", "Precipitation", "rainfall", "rain_mm"]
                ),
                wind_speed_kmh=get_float(
                    ["wind_speed", "wind", "Wind", "wind_kmh", "wind_speed_kmh"]
                ),
                conditions=row.get("conditions") or row.get("Conditions") or row.get("weather"),
                raw_data=row,
            )

        except Exception as e:
            self.logger.warning(f"Row {row_index}: Parse error - {e}")
            return None

    async def extract(self) -> ExtractionResult:
        """
        Extract data from CSV file.

        Returns:
            ExtractionResult containing WeatherRecord instances
        """
        result = self._create_result()
        records: list[WeatherRecord] = []

        try:
            # Determine if it's a URL or local file
            is_url = isinstance(self.file_path, str) and self.file_path.startswith("http")

            if is_url:
                source = str(self.file_path)
            else:
                path = self._resolve_path()
                if not path.exists():
                    # Try to generate sample data if file doesn't exist
                    if await self._generate_sample_data(path):
                        self.logger.info(f"Generated sample data at {path}")
                    else:
                        raise SourceConnectionError(
                            "csv",
                            f"File not found: {path}",
                        )
                source = str(path)

            self.logger.info(f"Reading CSV from {source}")

            # Read CSV with Polars
            try:
                df = pl.read_csv(
                    source,
                    infer_schema_length=1000,
                    null_values=["", "NA", "N/A", "null", "NULL", "None"],
                    ignore_errors=True,  # Continue on parse errors
                )
            except Exception as e:
                raise ExtractionError(
                    f"Failed to parse CSV: {e}",
                    source="csv",
                    recoverable=False,
                ) from e

            self.logger.info(
                f"CSV loaded: {len(df)} rows, {len(df.columns)} columns",
                extra={"columns": df.columns},
            )

            # Convert each row to WeatherRecord
            for i, row in enumerate(df.iter_rows(named=True)):
                record = self._parse_row_to_weather(row, i)
                if record:
                    records.append(record)
                else:
                    result.error_count += 1

            result.records = records  # type: ignore[assignment]
            self.logger.info(
                f"Extracted {len(records)} weather records",
                extra={
                    "total_rows": len(df),
                    "successful": len(records),
                    "failed": result.error_count,
                },
            )

        except (ExtractionError, SourceConnectionError):
            raise
        except Exception as e:
            self._handle_error(result, e)
            raise ExtractionError(
                f"CSV extraction failed: {e}",
                source="csv",
                recoverable=False,
            ) from e
        finally:
            result.complete()

        return result

    async def _generate_sample_data(self, path: Path) -> bool:
        """
        Generate sample weather data if file doesn't exist.

        This is for demonstration purposes - in production, you'd use real data.
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            # Generate sample weather data
            import random
            from datetime import timedelta

            locations = ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"]
            conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Stormy"]

            rows = []
            base_date = datetime(2026, 1, 1)

            for i in range(100):  # 100 sample records
                date = base_date + timedelta(days=i // 5, hours=(i % 5) * 6)
                rows.append(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "location": random.choice(locations),
                        "temperature": round(random.uniform(-5, 25), 1),
                        "humidity": round(random.uniform(30, 90), 1),
                        "precipitation": round(random.uniform(0, 20), 1)
                        if random.random() > 0.6
                        else 0,
                        "wind_speed": round(random.uniform(0, 50), 1),
                        "conditions": random.choice(conditions),
                    }
                )

            df = pl.DataFrame(rows)
            df.write_csv(path)
            return True

        except Exception as e:
            self.logger.warning(f"Failed to generate sample data: {e}")
            return False
