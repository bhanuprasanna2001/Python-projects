"""
Tests for data transformers.

These tests verify:
1. Transformers correctly clean and normalize data
2. Data validation catches quality issues
3. Deduplication works correctly
4. Transformer chain executes in order
"""

from datetime import UTC, datetime

from etl_pipeline.models import (
    BookRecord,
    DataSource,
    GitHubRepository,
    TransformedRecord,
    WeatherRecord,
)
from etl_pipeline.transformers.base import TransformerChain
from etl_pipeline.transformers.cleaners import DataCleaner
from etl_pipeline.transformers.normalizer import DataNormalizer
from etl_pipeline.transformers.validators import DataValidator


class TestDataCleaner:
    """Tests for the data cleaner transformer."""

    def test_cleans_github_repository(self, sample_github_repo: GitHubRepository):
        """Should convert GitHub repository to TransformedRecord."""
        cleaner = DataCleaner()

        result = cleaner.transform([sample_github_repo])

        assert len(result) == 1
        record = result[0]
        assert isinstance(record, TransformedRecord)
        assert record.source == DataSource.GITHUB
        assert record.source_id == "12345"
        assert record.title == "test-user/test-repo"
        assert record.numeric_value_1 == 100.0  # stars

    def test_cleans_weather_record(self, sample_weather_record: WeatherRecord):
        """Should convert weather record to TransformedRecord."""
        cleaner = DataCleaner()

        result = cleaner.transform([sample_weather_record])

        assert len(result) == 1
        record = result[0]
        assert record.source == DataSource.CSV
        assert "Berlin" in record.title
        assert record.numeric_value_1 == 5.5  # temperature

    def test_cleans_book_record(self, sample_book_record: BookRecord):
        """Should convert book record to TransformedRecord."""
        cleaner = DataCleaner()

        result = cleaner.transform([sample_book_record])

        assert len(result) == 1
        record = result[0]
        assert record.source == DataSource.SQLITE
        assert record.title == "The Great Gatsby"
        assert record.numeric_value_2 == 12.99  # price

    def test_drops_invalid_records_with_drop_strategy(self):
        """Should drop records missing required fields when strategy is 'drop'."""
        cleaner = DataCleaner(missing_strategy="drop")

        # Record missing required title
        invalid_book = BookRecord(
            title="",  # Empty title
            price=10.0,
            rating=3,
            raw_data={},
        )

        result = cleaner.transform([invalid_book])

        assert len(result) == 0

    def test_processes_mixed_record_types(self, multiple_extracted_records):
        """Should handle list with different record types."""
        cleaner = DataCleaner()

        result = cleaner.transform(multiple_extracted_records)

        assert len(result) == 3
        sources = {r.source for r in result}
        assert sources == {DataSource.GITHUB, DataSource.CSV, DataSource.SQLITE}


class TestDataNormalizer:
    """Tests for the data normalizer transformer."""

    def test_normalizes_timestamps_to_utc(self, sample_transformed_record: TransformedRecord):
        """Should convert all timestamps to UTC."""
        normalizer = DataNormalizer(normalize_dates=True)

        result = normalizer.transform([sample_transformed_record])

        assert len(result) == 1
        record = result[0]
        assert record.extracted_at.tzinfo is not None
        assert record.transformed_at.tzinfo is not None

    def test_deduplicates_by_source_identifier(self):
        """Should remove duplicates keeping most recent extraction."""
        normalizer = DataNormalizer(deduplicate=True)

        # Create two records with same source_identifier
        record1 = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="123",
            title="Duplicate Record",
            extracted_at=datetime(2026, 1, 1),
        )
        record2 = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="123",  # Same source_id
            title="Duplicate Record Updated",
            extracted_at=datetime(2026, 1, 20),  # More recent
        )

        result = normalizer.transform([record1, record2])

        assert len(result) == 1
        assert result[0].title == "Duplicate Record Updated"

    def test_normalizes_tags_to_lowercase(self, sample_transformed_record: TransformedRecord):
        """Should normalize tags to lowercase."""
        sample_transformed_record.tags = ["Python", "ETL", "TESTING", "Python"]  # With duplicate
        normalizer = DataNormalizer()

        result = normalizer.transform([sample_transformed_record])

        assert result[0].tags == ["python", "etl", "testing"]

    def test_preserves_records_when_deduplication_disabled(self):
        """Should keep all records when deduplication is disabled."""
        normalizer = DataNormalizer(deduplicate=False)

        record1 = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="123",
            title="Record 1",
            extracted_at=datetime(2026, 1, 1),
        )
        record2 = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="123",
            title="Record 2",
            extracted_at=datetime(2026, 1, 2),
        )

        result = normalizer.transform([record1, record2])

        assert len(result) == 2


class TestDataValidator:
    """Tests for the data validator transformer."""

    def test_validates_complete_record(self, sample_transformed_record: TransformedRecord):
        """Should pass valid records through validation."""
        validator = DataValidator()

        result = validator.transform([sample_transformed_record])

        assert len(result) == 1
        assert validator.metrics is not None
        assert validator.metrics.valid_records == 1

    def test_rejects_record_missing_source_id(self):
        """Should reject records without source_id."""
        validator = DataValidator()

        invalid_record = TransformedRecord(
            source=DataSource.GITHUB,
            source_id="",  # Missing
            title="Valid Title",
            extracted_at=datetime.now(UTC),
        )

        result = validator.transform([invalid_record])

        assert len(result) == 0
        assert validator.metrics.invalid_records == 1

    def test_calculates_completeness_ratio(self):
        """Should calculate correct completeness metrics."""
        validator = DataValidator()

        records = [
            TransformedRecord(
                source=DataSource.GITHUB,
                source_id="1",
                title="Valid",
                extracted_at=datetime.now(UTC),
            ),
            TransformedRecord(
                source=DataSource.GITHUB,
                source_id="",  # Invalid
                title="",  # Invalid
                extracted_at=datetime.now(UTC),
            ),
        ]

        result = validator.transform(records)

        assert len(result) == 1
        assert validator.metrics.validity_ratio == 0.5

    def test_generates_quality_report(self, sample_transformed_record: TransformedRecord):
        """Should generate detailed quality report."""
        validator = DataValidator()
        validator.transform([sample_transformed_record])

        report = validator.get_quality_report()

        assert "summary" in report
        assert "completeness" in report
        assert "thresholds" in report
        assert report["summary"]["valid_records"] == 1


class TestTransformerChain:
    """Tests for transformer chain execution."""

    def test_executes_transformers_in_order(self, multiple_extracted_records):
        """Should execute transformers in sequence."""
        chain = TransformerChain(
            [
                DataCleaner(),
                DataNormalizer(),
                DataValidator(),
            ]
        )

        result = chain.execute(multiple_extracted_records)

        assert result.success
        assert result.input_count == 3
        assert result.output_count == 3  # All valid in our fixtures

    def test_tracks_dropped_records(self):
        """Should track records dropped during transformation."""
        chain = TransformerChain(
            [
                DataCleaner(missing_strategy="drop"),
                DataValidator(),
            ]
        )

        # Mix of valid and invalid records
        records = [
            GitHubRepository(
                repo_id=1,
                name="valid",
                full_name="user/valid",
                html_url="https://github.com/user/valid",
                raw_data={},
            ),
            BookRecord(
                title="",  # Will be dropped
                raw_data={},
            ),
        ]

        result = chain.execute(records)

        assert result.input_count == 2
        assert result.output_count == 1
        assert result.dropped_count >= 1

    def test_empty_input_produces_empty_output(self):
        """Should handle empty input gracefully."""
        chain = TransformerChain([DataCleaner()])

        result = chain.execute([])

        assert result.success
        assert result.input_count == 0
        assert result.output_count == 0
