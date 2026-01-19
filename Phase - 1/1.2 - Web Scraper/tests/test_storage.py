"""Tests for SQLite storage.

WHY TEST THIS:
- Risk: CRITICAL - data loss or corruption is unacceptable
- Complexity: MEDIUM - SQL operations, file handling
- Easy to test: YES - use temp database, verify contents

WHAT WE'RE TESTING:
1. Save books → can retrieve them
2. Deduplication → same title not stored twice
3. Count → returns correct number
4. Clear → removes all data
"""

import tempfile
from pathlib import Path

import pytest
from web_scraper.models import Book
from web_scraper.storage.sqlite_storage import SQLiteStorage


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database file for testing.

    Using a temp file ensures tests don't affect real data
    and tests are isolated from each other.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield Path(f.name)
    # Cleanup after test
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def storage(temp_db: Path) -> SQLiteStorage:
    """Create a fresh SQLiteStorage instance for each test."""
    return SQLiteStorage(db_path=temp_db)


@pytest.fixture
def sample_books() -> list[Book]:
    """Sample books for testing."""
    return [
        Book(title="Book One", price="£10.00", rating="Five"),
        Book(title="Book Two", price="£20.00", rating="Four"),
        Book(title="Book Three", price="£30.00", rating="Three"),
    ]


class TestSQLiteStorageSave:
    """Test saving books to database."""

    def test_save_books_returns_count(
        self, storage: SQLiteStorage, sample_books: list[Book]
    ) -> None:
        """Save should return number of books saved.

        Reasoning: Caller needs to know how many were actually saved
        (may differ from input due to deduplication).
        """
        saved = storage.save(sample_books)

        assert saved == 3

    def test_save_empty_list_returns_zero(self, storage: SQLiteStorage) -> None:
        """Saving empty list should return 0, not error.

        Reasoning: Empty input is valid - nothing to save.
        """
        saved = storage.save([])

        assert saved == 0

    def test_saved_books_are_retrievable(
        self, storage: SQLiteStorage, sample_books: list[Book]
    ) -> None:
        """Saved books should be retrievable via get_all.

        Reasoning: Core functionality - what goes in must come out.
        """
        storage.save(sample_books)

        retrieved = storage.get_all()

        assert len(retrieved) == 3
        titles = {book.title for book in retrieved}
        assert titles == {"Book One", "Book Two", "Book Three"}


class TestSQLiteStorageDeduplication:
    """Test deduplication via UNIQUE constraint.

    THIS IS CRITICAL - deduplication prevents data bloat
    and ensures data integrity.
    """

    def test_duplicate_titles_ignored(self, storage: SQLiteStorage) -> None:
        """Books with same title should not be stored twice.

        Reasoning: Title is our unique identifier. Storing duplicates
        would waste space and cause counting issues.
        """
        book = Book(title="Duplicate Book", price="£10.00", rating="Five")

        # Save same book twice
        storage.save([book])
        storage.save([book])

        # Should only have one
        assert storage.count() == 1

    def test_deduplication_returns_correct_count(self, storage: SQLiteStorage) -> None:
        """Save should return only NEW books saved, not duplicates.

        Reasoning: Caller needs accurate count for logging/progress.
        """
        book = Book(title="Test Book", price="£10.00", rating="Five")

        first_save = storage.save([book])
        second_save = storage.save([book])

        assert first_save == 1  # New book
        assert second_save == 0  # Duplicate, not saved

    def test_partial_duplicates_handled(self, storage: SQLiteStorage) -> None:
        """Mix of new and duplicate books should save only new ones.

        Reasoning: Real scraping often re-encounters some books.
        """
        books_batch_1 = [
            Book(title="Book A", price="£10.00", rating="Five"),
            Book(title="Book B", price="£20.00", rating="Four"),
        ]
        books_batch_2 = [
            Book(title="Book B", price="£20.00", rating="Four"),  # Duplicate
            Book(title="Book C", price="£30.00", rating="Three"),  # New
        ]

        storage.save(books_batch_1)
        saved = storage.save(books_batch_2)

        assert saved == 1  # Only Book C is new
        assert storage.count() == 3  # A, B, C


class TestSQLiteStorageCount:
    """Test count functionality."""

    def test_count_empty_database(self, storage: SQLiteStorage) -> None:
        """Empty database should return count of 0."""
        assert storage.count() == 0

    def test_count_after_save(self, storage: SQLiteStorage, sample_books: list[Book]) -> None:
        """Count should reflect saved books."""
        storage.save(sample_books)

        assert storage.count() == 3


class TestSQLiteStorageClear:
    """Test clear functionality."""

    def test_clear_removes_all_books(
        self, storage: SQLiteStorage, sample_books: list[Book]
    ) -> None:
        """Clear should remove all books from database.

        Reasoning: Useful for testing and reset scenarios.
        """
        storage.save(sample_books)
        assert storage.count() == 3

        storage.clear()

        assert storage.count() == 0

    def test_clear_empty_database_no_error(self, storage: SQLiteStorage) -> None:
        """Clearing empty database should not raise error."""
        storage.clear()  # Should not raise

        assert storage.count() == 0


class TestSQLiteStorageLastScraped:
    """Test last_scraped timestamp tracking."""

    def test_last_scraped_returns_none_when_empty(self, storage: SQLiteStorage) -> None:
        """Empty database should return None for last_scraped."""
        assert storage.get_last_scraped() is None

    def test_last_scraped_returns_timestamp_after_save(
        self, storage: SQLiteStorage, sample_books: list[Book]
    ) -> None:
        """Should return timestamp after saving books.

        Reasoning: Enables incremental scraping - know when we last ran.
        """
        storage.save(sample_books)

        last_scraped = storage.get_last_scraped()

        assert last_scraped is not None
