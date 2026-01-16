"""Books model"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

@dataclass(frozen=True)
class Book:
    """Immutable book representation
    
    Attributes:
        price: Book price
        title: Book title
        rating: Book rating
        category: Book category
        id: Unique book identifier
    """
    
    title: str
    price: float | None = None
    rating: float | None = None
    
    def __post_init__(self) -> None:
        """Validate book data"""
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")
        if len(self.title) > 200:
            raise ValueError("Title cannot exceed 200 characters")
        if self.price and self.price < 0.0:
            raise ValueError("Price cannot be less than 0")
        
        
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
            
    