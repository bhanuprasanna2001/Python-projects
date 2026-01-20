"""CSV file storage implementation."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import ClassVar

from web_scraper.models import Book
from web_scraper.storage.base import Storage

logger = logging.getLogger(__name__)


class CSVStorage(Storage):
    """Stores books in a CSV file.

    Note: CSV storage appends data without deduplication.
    Use SQLite for deduplication. CSV is best for exports.
    """

    FIELDNAMES: ClassVar[list[str]] = ["title", "price", "rating"]

    def __init__(self, file_path: str | Path = "data/books.csv") -> None:
        """Initialize CSV storage.

        Args:
            file_path: Path to CSV file (created if doesn't exist)
        """
        self._path = Path(file_path)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create parent directory if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _file_exists_with_data(self) -> bool:
        """Check if file exists and has content."""
        return self._path.exists() and self._path.stat().st_size > 0

    def save(self, books: list[Book]) -> int:
        """Append books to CSV file.

        Returns:
            Number of books saved (always len(books) for CSV)
        """
        if not books:
            return 0

        write_header = not self._file_exists_with_data()

        with self._path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)

            if write_header:
                writer.writeheader()

            for book in books:
                writer.writerow(
                    {
                        "title": book.title,
                        "price": book.price or "",
                        "rating": book.rating or "",
                    }
                )

        logger.info(f"Saved {len(books)} books to {self._path}")
        return len(books)

    def get_all(self) -> list[Book]:
        """Read all books from CSV file."""
        if not self._file_exists_with_data():
            return []

        books = []
        with self._path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                books.append(
                    Book(
                        title=row["title"],
                        price=row["price"] or None,
                        rating=row["rating"] or None,
                    )
                )
        return books

    def count(self) -> int:
        """Count books in CSV (requires reading file)."""
        return len(self.get_all())

    def clear(self) -> None:
        """Delete the CSV file."""
        if self._path.exists():
            self._path.unlink()
            logger.info(f"Cleared {self._path}")
