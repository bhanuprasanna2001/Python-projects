"""Books model"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    """Immutable book representation.
    
    Attributes:
        title: Book title
        price: Book price as string (e.g., "£51.77")
        rating: Book rating as string (e.g., "Three")
    """
    
    title: str
    price: str | None = None
    rating: str | None = None
    
    def __post_init__(self) -> None:
        """Validate book data."""
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")
        if len(self.title) > 200:
            raise ValueError("Title cannot exceed 200 characters")
        
        
    def with_updates(
        self,
        title: str | None = None,
        price: float | None = None,
        rating: float | None = None,
    ) -> Book:
        """Create a new Book with updated fields"""
        return Book(
            title = title if title is not None else self.title,
            price = price if price is not None else self.price,
            rating = rating if rating is not None else self.rating,
        )
            
    