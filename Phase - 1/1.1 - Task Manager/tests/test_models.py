"""Tests for Task model."""

from datetime import datetime

import pytest
from task_manager.models import Priority, Task


class TestPriority:
    """Tests for Priority enum."""

    def test_from_string_valid(self):
        assert Priority.from_string("HIGH") == Priority.HIGH
        assert Priority.from_string("medium") == Priority.MEDIUM
        assert Priority.from_string("Low") == Priority.LOW

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid priority"):
            Priority.from_string("URGENT")


class TestTask:
    """Tests for Task dataclass."""

    def test_create_minimal(self):
        task = Task(title="Test task")
        assert task.title == "Test task"
        assert task.description == ""
        assert task.is_completed is False
        assert task.priority == Priority.MEDIUM

    def test_create_full(self):
        due = datetime(2026, 12, 31, 23, 59)
        task = Task(
            title="Full task",
            description="A complete task",
            is_completed=True,
            priority=Priority.HIGH,
            due_date=due,
            category="Work",
        )
        assert task.title == "Full task"
        assert task.is_completed is True
        assert task.due_date == due

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Task(title="")

    def test_whitespace_title_raises(self):
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Task(title="   ")

    def test_title_too_long_raises(self):
        with pytest.raises(ValueError, match="Title cannot exceed 200"):
            Task(title="x" * 201)

    def test_description_too_long_raises(self):
        with pytest.raises(ValueError, match="Description cannot exceed 1000"):
            Task(title="Test", description="x" * 1001)

    def test_category_too_long_raises(self):
        with pytest.raises(ValueError, match="Category cannot exceed 50"):
            Task(title="Test", category="x" * 51)

    def test_immutability(self):
        task = Task(title="Test")
        with pytest.raises(AttributeError):
            task.title = "Changed"

    def test_with_updates(self):
        task = Task(title="Original", priority=Priority.LOW)
        updated = task.with_updates(title="Updated", priority=Priority.HIGH)

        # Original unchanged
        assert task.title == "Original"
        assert task.priority == Priority.LOW

        # New task has updates
        assert updated.title == "Updated"
        assert updated.priority == Priority.HIGH

    def test_with_updates_partial(self):
        task = Task(title="Test", description="Desc", category="Work")
        updated = task.with_updates(description="New desc")

        assert updated.title == "Test"  # Unchanged
        assert updated.description == "New desc"  # Changed
        assert updated.category == "Work"  # Unchanged

    def test_toggle_completed(self):
        task = Task(title="Test", is_completed=False)
        toggled = task.toggle_completed()

        assert task.is_completed is False  # Original unchanged
        assert toggled.is_completed is True

        toggled_back = toggled.toggle_completed()
        assert toggled_back.is_completed is False
