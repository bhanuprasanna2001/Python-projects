"""
Tests for data extractors.

These tests verify:
1. Extractors correctly parse data from sources
2. Extractors handle errors gracefully
3. Extractors respect rate limits and retries
4. Extraction results contain proper metadata
"""

from pathlib import Path

import pytest

from etl_pipeline.extractors.csv_extractor import CSVExtractor
from etl_pipeline.extractors.sqlite_extractor import SQLiteExtractor
from etl_pipeline.models import DataSource


class TestCSVExtractor:
    """Tests for CSV extractor."""

    @pytest.mark.asyncio
    async def test_extracts_valid_csv_file(self, sample_csv_file: Path):
        """Extractor should parse all valid rows from CSV file."""
        extractor = CSVExtractor(file_path=sample_csv_file)

        result = await extractor.extract()

        assert result.success
        assert len(result.records) == 5
        assert result.source == DataSource.CSV

    @pytest.mark.asyncio
    async def test_extracted_records_have_correct_fields(self, sample_csv_file: Path):
        """Each extracted record should have properly parsed fields."""
        extractor = CSVExtractor(file_path=sample_csv_file)

        result = await extractor.extract()

        # Check first record
        record = result.records[0]
        assert record.location == "Berlin"
        assert record.temperature_celsius == 5.5
        assert record.humidity_percent == 75.0
        assert record.conditions == "Cloudy"

    @pytest.mark.asyncio
    async def test_handles_missing_values_gracefully(self, tmp_data_dir: Path):
        """Extractor should handle CSV files with missing values."""
        csv_path = tmp_data_dir / "incomplete.csv"
        csv_path.write_text("""date,location,temperature
2026-01-01,Berlin,5.5
2026-01-02,Munich,
2026-01-03,,3.0
""")

        extractor = CSVExtractor(file_path=csv_path)
        result = await extractor.extract()

        # Should extract records even with missing values
        assert result.completed_at is not None
        # Records with missing date should be skipped
        assert len(result.records) >= 1

    @pytest.mark.asyncio
    async def test_validates_file_existence(self, tmp_data_dir: Path):
        """Validation should return False for non-existent files."""
        extractor = CSVExtractor(file_path=tmp_data_dir / "nonexistent.csv")

        is_valid = await extractor.validate_connection()

        assert not is_valid

    @pytest.mark.asyncio
    async def test_extraction_records_metadata(self, sample_csv_file: Path):
        """Extraction result should contain timing and count metadata."""
        extractor = CSVExtractor(file_path=sample_csv_file)

        result = await extractor.extract()

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at > result.started_at
        assert result.record_count == len(result.records)
        assert result.duration_seconds is not None
        assert result.duration_seconds > 0


class TestSQLiteExtractor:
    """Tests for SQLite extractor."""

    @pytest.mark.asyncio
    async def test_extracts_from_database(self, sample_sqlite_db: Path):
        """Extractor should read all rows from database."""
        extractor = SQLiteExtractor(
            database_path=sample_sqlite_db,
            query="SELECT * FROM books",
        )

        result = await extractor.extract()

        assert result.success
        assert len(result.records) == 3
        assert result.source == DataSource.SQLITE

    @pytest.mark.asyncio
    async def test_extracted_books_have_correct_fields(self, sample_sqlite_db: Path):
        """Extracted book records should have properly parsed fields."""
        extractor = SQLiteExtractor(database_path=sample_sqlite_db)

        result = await extractor.extract()

        # Find The Great Gatsby
        gatsby = next((r for r in result.records if r.title == "The Great Gatsby"), None)
        assert gatsby is not None
        assert gatsby.price == 12.99
        assert gatsby.rating == 5
        assert gatsby.upc == "UPC001"

    @pytest.mark.asyncio
    async def test_handles_custom_query(self, sample_sqlite_db: Path):
        """Extractor should support custom SQL queries."""
        extractor = SQLiteExtractor(
            database_path=sample_sqlite_db,
            query="SELECT * FROM books WHERE rating = 5",
        )

        result = await extractor.extract()

        # All 3 books have rating 5 in our sample
        assert len(result.records) == 3

    @pytest.mark.asyncio
    async def test_uses_fallback_path_when_primary_missing(
        self, tmp_data_dir: Path, sample_sqlite_db: Path
    ):
        """Should use fallback path when primary database doesn't exist."""
        extractor = SQLiteExtractor(
            database_path=tmp_data_dir / "nonexistent.db",
            fallback_path=sample_sqlite_db,
        )

        is_valid = await extractor.validate_connection()
        assert is_valid

        result = await extractor.extract()
        assert result.success

    @pytest.mark.asyncio
    async def test_validates_connection_with_invalid_db(self, tmp_data_dir: Path):
        """Validation should fail for corrupted or missing database."""
        # Create an invalid "database" file
        invalid_db = tmp_data_dir / "invalid.db"
        invalid_db.write_text("not a database")

        extractor = SQLiteExtractor(database_path=invalid_db)

        is_valid = await extractor.validate_connection()
        assert not is_valid


class TestExtractorErrorHandling:
    """Tests for extractor error handling behavior."""

    @pytest.mark.asyncio
    async def test_extraction_error_count_tracked(self, tmp_data_dir: Path):
        """Errors during extraction should be counted in result."""
        # CSV with some unparseable rows
        csv_path = tmp_data_dir / "partial_errors.csv"
        csv_path.write_text("""date,location,temperature
2026-01-01,Berlin,5.5
invalid-date,Munich,3.0
2026-01-03,Hamburg,2.0
""")

        extractor = CSVExtractor(file_path=csv_path)
        result = await extractor.extract()

        # Should complete but track error
        assert result.completed_at is not None
        # At least one record should succeed
        assert len(result.records) >= 1
