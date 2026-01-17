"""Abstract base class for storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from web_scraper.models import Book


class Storage(ABC):
    """Abstract interface for data storage.

    All storage implementations must implement these methods.
    This enables swapping CSV/SQLite without changing calling code.
    """

    @abstractmethod
    def save(self, books: list[Book]) -> int:
        """Save books to storage.

        Args:
            books: List of Book objects to save

        Returns:
            Number of books actually saved (may be less due to deduplication)
        """
        pass

    @abstractmethod
    def get_all(self) -> list[Book]:
        """Retrieve all stored books.

        Returns:
            List of all Book objects in storage
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Get total number of stored books.

        Returns:
            Count of books in storage
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Remove all data from storage."""
        pass
