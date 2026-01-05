"""Task model and related types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Priority(Enum):
    """Task priority levels."""
    
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    
    @classmethod
    def from_string(cls, value: str) -> Priority:
        """Parse priority from string, case-insensitive."""
        try:
            return cls[value.upper()]
        except KeyError:
            valid = ", ".join(p.value for p in cls)
            raise ValueError(f"Invalid priority '{value}'. Must be one of: {valid}")


@dataclass(frozen=True)
class Task:
    """Immutable task representation.
    
    Attributes:
        id: Unique task identifier (None for new tasks).
        title: Task title (required).
        description: Task description.
        is_completed: Completion status.
        created_at: Creation timestamp.
        priority: Task priority level.
        due_date: Optional due date.
        category: Task category.
    """
    
    title: str
    description: str = ""
    is_completed: bool = False
    created_at: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    due_date: Optional[datetime] = None
    category: str = ""
    id: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Validate task data."""
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")
        if len(self.title) > 200:
            raise ValueError("Title cannot exceed 200 characters")
        if len(self.description) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")
        if len(self.category) > 50:
            raise ValueError("Category cannot exceed 50 characters")
    
    def with_updates(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_completed: Optional[bool] = None,
        priority: Optional[Priority] = None,
        due_date: Optional[datetime] = None,
        category: Optional[str] = None,
    ) -> Task:
        """Create a new Task with updated fields."""
        return Task(
            id=self.id,
            title=title if title is not None else self.title,
            description=description if description is not None else self.description,
            is_completed=is_completed if is_completed is not None else self.is_completed,
            created_at=self.created_at,
            priority=priority if priority is not None else self.priority,
            due_date=due_date if due_date is not None else self.due_date,
            category=category if category is not None else self.category,
        )
    
    def toggle_completed(self) -> Task:
        """Return a new Task with toggled completion status."""
        return self.with_updates(is_completed=not self.is_completed)
