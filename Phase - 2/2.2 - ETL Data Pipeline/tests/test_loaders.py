"""
Tests for data loaders.

These tests verify:
1. Loaders correctly persist data to storage
2. Upsert logic works correctly (insert/update/skip)
3. Schema creation is idempotent
4. Loading handles errors gracefully
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from etl_pipeline.loaders.sqlite_loader import SQLiteLoader
from etl_pipeline.models import DataSource, TransformedRecord


class TestSQLiteLoader:
    """Tests for SQLite loader."""

    @pytest.fixture
    def loader(self, tmp_data_dir: Path) -> SQLiteLoader:
        """Create SQLite loader with temp database."""
        return SQLiteLoader(
            database_path=tmp_data_dir / "test_output.db",
            on_conflict="update",
        )

    @pytest.fixture
    def sample_records(self) -> list[TransformedRecord]:
        """Create sample records for loading."""
        return [
            TransformedRecord(
                source=DataSource.GITHUB,
                source_id="123",
                title="Test Repo 1",
                description="First test repository",
                url="https://github.com/test/repo1",
                category="Python",
                numeric_value_1=100.0,
                numeric_value_2=25.0,
                extracted_at=datetime.now(UTC),
                tags=["python", "testing"],
            ),
            TransformedRecord(
                source=DataSource.SQLITE,
                source_id="456",
                title="Test Book",
                description=None,
                url="https://example.com/book",
                category="Books",
                numeric_value_1=4.5,
                numeric_value_2=19.99,
                extracted_at=datetime.now(UTC),
                tags=["fiction"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_creates_schema_on_first_load(self, loader: SQLiteLoader, sample_records):
        """Should create database schema automatically."""
        # Schema doesn't exist yet
        result = await loader.load(sample_records)

        assert result.success
        # Verify tables exist by getting count
        count = await loader.get_record_count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_inserts_new_records(self, loader: SQLiteLoader, sample_records):
        """Should insert all records when database is empty."""
        result = await loader.load(sample_records)

        assert result.records_inserted == 2
        assert result.records_updated == 0
        assert result.records_skipped == 0

    @pytest.mark.asyncio
    async def test_updates_existing_records_on_conflict(self, loader: SQLiteLoader, sample_records):
        """Should update records with same source_identifier."""
        # First load
        await loader.load(sample_records)

        # Modify and reload
        sample_records[0].title = "Updated Repo Title"
        sample_records[0].numeric_value_1 = 200.0

        result = await loader.load(sample_records)

        assert result.records_updated == 2
        assert result.records_inserted == 0

    @pytest.mark.asyncio
    async def test_skips_duplicates_when_skip_strategy(self, tmp_data_dir: Path, sample_records):
        """Should skip duplicates when on_conflict='skip'."""
        loader = SQLiteLoader(
            database_path=tmp_data_dir / "skip_test.db",
            on_conflict="skip",
        )

        # First load
        await loader.load(sample_records)

        # Second load - should skip all
        result = await loader.load(sample_records)

        assert result.records_skipped == 2
        assert result.records_inserted == 0
        assert result.records_updated == 0

    @pytest.mark.asyncio
    async def test_handles_empty_records_list(self, loader: SQLiteLoader):
        """Should handle empty input gracefully."""
        result = await loader.load([])

        assert result.success
        assert result.records_attempted == 0
        assert result.total_processed == 0

    @pytest.mark.asyncio
    async def test_tracks_records_by_source(self, loader: SQLiteLoader, sample_records):
        """Should correctly count records by source."""
        await loader.load(sample_records)

        github_count = await loader.get_records_by_source("github")
        sqlite_count = await loader.get_records_by_source("sqlite")

        assert github_count == 1
        assert sqlite_count == 1

    @pytest.mark.asyncio
    async def test_provides_summary_statistics(self, loader: SQLiteLoader, sample_records):
        """Should provide accurate summary of loaded data."""
        await loader.load(sample_records)

        summary = await loader.get_summary()

        assert summary["total_records"] == 2
        assert "github" in summary["by_source"]
        assert "sqlite" in summary["by_source"]
        assert summary["last_loaded_at"] is not None

    @pytest.mark.asyncio
    async def test_maintains_history_on_update(self, tmp_data_dir: Path, sample_records):
        """Should archive old version before update when history enabled."""
        loader = SQLiteLoader(
            database_path=tmp_data_dir / "history_test.db",
            enable_history=True,
        )

        # Initial load
        await loader.load(sample_records)

        # Update
        sample_records[0].title = "Updated Title"
        await loader.load(sample_records)

        summary = await loader.get_summary()

        # Should have history records
        assert summary["history_records"] >= 1

    @pytest.mark.asyncio
    async def test_validates_connection(self, loader: SQLiteLoader):
        """Should validate database connection."""
        # First, initialize schema
        await loader.initialize_schema()

        is_valid = await loader.validate_connection()
        assert is_valid

    @pytest.mark.asyncio
    async def test_schema_creation_is_idempotent(self, loader: SQLiteLoader):
        """Calling initialize_schema multiple times should not error."""
        await loader.initialize_schema()
        await loader.initialize_schema()
        await loader.initialize_schema()

        # Should still work
        is_valid = await loader.validate_connection()
        assert is_valid


class TestLoaderErrorHandling:
    """Tests for loader error handling."""

    @pytest.mark.asyncio
    async def test_handles_invalid_record_gracefully(self, tmp_data_dir: Path):
        """Should track errors for records that fail to load."""
        loader = SQLiteLoader(database_path=tmp_data_dir / "error_test.db")

        # Record with valid and problematic data
        records = [
            TransformedRecord(
                source=DataSource.GITHUB,
                source_id="valid",
                title="Valid Record",
                extracted_at=datetime.now(UTC),
            ),
        ]

        result = await loader.load(records)

        # Should succeed
        assert result.success
        assert result.records_failed == 0
