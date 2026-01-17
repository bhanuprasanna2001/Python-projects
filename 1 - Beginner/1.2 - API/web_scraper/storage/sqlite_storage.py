"""SQLite database storage implementation."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from web_scraper.models import Book
from web_scraper.storage.base import Storage

logger = logging.getLogger(__name__)


class SQLiteStorage(Storage):
    """Stores books in SQLite database with automatic deduplication.

    Uses UNIQUE constraint on title to prevent duplicates.
    Tracks scrape timestamp for incremental scraping support.
    """

    _CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            price TEXT,
            rating TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    _INSERT_SQL = """
        INSERT OR IGNORE INTO books (title, price, rating, scraped_at)
        VALUES (?, ?, ?, ?)
    """

    def __init__(self, db_path: str | Path = "data/scraper.db") -> None:
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self._path = Path(db_path)
        self._ensure_directory()
        self._init_schema()

    def _ensure_directory(self) -> None:
        """Create parent directory if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        with self._connection() as conn:
            conn.execute(self._CREATE_TABLE_SQL)
        logger.debug(f"Initialized database at {self._path}")

    def save(self, books: list[Book]) -> int:
        """Save books to database, skipping duplicates.

        Returns:
            Number of NEW books saved (excludes duplicates)
        """
        if not books:
            return 0

        now = datetime.now().isoformat()

        with self._connection() as conn:
            cursor = conn.cursor()

            # Get count before insert
            cursor.execute("SELECT COUNT(*) FROM books")
            count_before = cursor.fetchone()[0]

            # Batch insert (INSERT OR IGNORE skips duplicates)
            cursor.executemany(
                self._INSERT_SQL, [(book.title, book.price, book.rating, now) for book in books]
            )

            # Get count after insert
            cursor.execute("SELECT COUNT(*) FROM books")
            result = cursor.fetchone()
            count_after: int = int(result[0]) if result else 0

        saved: int = count_after - count_before
        skipped = len(books) - saved

        if skipped > 0:
            logger.info(f"Saved {saved} books, skipped {skipped} duplicates")
        else:
            logger.info(f"Saved {saved} books to {self._path}")

        return saved

    def get_all(self) -> list[Book]:
        """Retrieve all books from database."""
        with self._connection() as conn:
            cursor = conn.execute("SELECT title, price, rating FROM books ORDER BY id")
            return [
                Book(title=row["title"], price=row["price"], rating=row["rating"])
                for row in cursor.fetchall()
            ]

    def count(self) -> int:
        """Get total number of books in database."""
        with self._connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM books")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def clear(self) -> None:
        """Delete all books from database."""
        with self._connection() as conn:
            conn.execute("DELETE FROM books")
        logger.info("Cleared all books from database")

    def get_last_scraped(self) -> datetime | None:
        """Get timestamp of most recent scrape.

        Useful for incremental scraping decisions.
        """
        with self._connection() as conn:
            cursor = conn.execute("SELECT MAX(scraped_at) FROM books")
            result = cursor.fetchone()[0]
            return datetime.fromisoformat(result) if result else None
