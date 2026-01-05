"""Business logic layer for task operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from task_manager.models import Priority, Task
from task_manager.repository import TaskRepository


class TaskNotFoundError(Exception):
    """Raised when a task is not found."""
    pass


class TaskService:
    """Orchestrates task operations between CLI and repository.
    
    This service layer contains all business logic and validation,
    keeping the repository focused purely on data access.
    """
    
    def __init__(self, repository: TaskRepository) -> None:
        """Initialize service with a repository."""
        self._repo = repository
    
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: Optional[datetime] = None,
        category: str = "",
    ) -> Task:
        """Create and persist a new task."""
        if due_date and due_date < datetime.now():
            raise ValueError("Due date cannot be in the past")
        
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            category=category,
        )
        return self._repo.create(task)
    
    def get_task(self, task_id: int) -> Task:
        """Get a task by ID."""
        task = self._repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} not found")
        return task
    
    def list_tasks(self, sort_by: Optional[str] = None) -> Sequence[Task]:
        """Get all tasks, optionally sorted."""
        if sort_by:
            return self._repo.get_sorted(sort_by)
        return self._repo.get_all()
    
    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[Priority] = None,
        due_date: Optional[datetime] = None,
        category: Optional[str] = None,
    ) -> Task:
        """Update an existing task."""
        task = self.get_task(task_id)
        
        if due_date and due_date < datetime.now():
            raise ValueError("Due date cannot be in the past")
        
        updated = task.with_updates(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            category=category,
        )
        self._repo.update(updated)
        return updated
    
    def delete_task(self, task_id: int) -> None:
        """Delete a task by ID."""
        if not self._repo.delete(task_id):
            raise TaskNotFoundError(f"Task with ID {task_id} not found")
    
    def toggle_completed(self, task_id: int) -> Task:
        """Toggle the completion status of a task."""
        task = self.get_task(task_id)
        toggled = task.toggle_completed()
        self._repo.update(toggled)
        return toggled
    
    def search_by_priority(self, priority: Priority) -> Sequence[Task]:
        """Find all tasks with given priority."""
        return self._repo.find_by_priority(priority)
    
    def search_by_category(self, category: str) -> Sequence[Task]:
        """Find all tasks with given category."""
        return self._repo.find_by_category(category)
    
    def search_by_date_range(
        self, field: str, start: datetime, end: datetime
    ) -> Sequence[Task]:
        """Find tasks within a date range."""
        if start > end:
            raise ValueError("Start date must be before end date")
        return self._repo.find_by_date_range(field, start, end)
