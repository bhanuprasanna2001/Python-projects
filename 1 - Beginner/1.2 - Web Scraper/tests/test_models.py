"""Tests for Book model validation.

WHY TEST THIS:
- Risk: MEDIUM - invalid data could cause issues downstream
- Complexity: LOW - simple validation rules
- Easy to test: YES - just instantiate and check

WHAT WE'RE TESTING:
1. Valid data → Book created successfully
2. Empty title → ValueError
3. Title too long → ValueError
"""

import pytest
from web_scraper.models import Book


class TestBookValidation:
    """Test Book dataclass validation."""

    def test_valid_book_creation(self) -> None:
        """Valid data should create Book without error."""
        book = Book(title="Test Book", price="£10.00", rating="Five")

        assert book.title == "Test Book"
        assert book.price == "£10.00"
        assert book.rating == "Five"

    def test_book_with_optional_fields_none(self) -> None:
        """Book can be created with only title."""
        book = Book(title="Minimal Book")

        assert book.title == "Minimal Book"
        assert book.price is None
        assert book.rating is None

    def test_empty_title_raises_error(self) -> None:
        """Empty title should raise ValueError.

        Reasoning: Title is required - a book without title is meaningless.
        """
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Book(title="")

    def test_whitespace_only_title_raises_error(self) -> None:
        """Whitespace-only title should raise ValueError.

        Reasoning: Whitespace is effectively empty.
        """
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Book(title="   ")

    def test_title_too_long_raises_error(self) -> None:
        """Title over 200 characters should raise ValueError.

        Reasoning: Sanity check - prevents garbage data.
        """
        long_title = "A" * 201

        with pytest.raises(ValueError, match="cannot exceed 200 characters"):
            Book(title=long_title)

    def test_title_at_max_length_allowed(self) -> None:
        """Title exactly 200 characters should be allowed."""
        title_200 = "A" * 200

        book = Book(title=title_200)

        assert len(book.title) == 200


class TestBookImmutability:
    """Test that Book is immutable (frozen dataclass)."""

    def test_cannot_modify_title(self) -> None:
        """Book fields should not be modifiable.

        Reasoning: Immutability prevents accidental data corruption.
        """
        book = Book(title="Original")

        with pytest.raises(AttributeError):
            book.title = "Modified"


class TestBookEquality:
    """Test Book equality comparison."""

    def test_books_with_same_data_are_equal(self) -> None:
        """Two Books with same values should be equal.

        Reasoning: Value object semantics - equality by value, not identity.
        """
        book1 = Book(title="Same", price="£10.00", rating="Five")
        book2 = Book(title="Same", price="£10.00", rating="Five")

        assert book1 == book2

    def test_books_with_different_data_not_equal(self) -> None:
        """Books with different values should not be equal."""
        book1 = Book(title="Book One", price="£10.00", rating="Five")
        book2 = Book(title="Book Two", price="£10.00", rating="Five")

        assert book1 != book2
