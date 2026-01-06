"""Tests for TaskService."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from task_manager.models import Priority
from task_manager.repository import TaskRepository
from task_manager.service import TaskNotFoundError, TaskService


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def service(temp_db):
    """Create a service with a temporary database."""
    repository = TaskRepository(temp_db)
    return TaskService(repository)


class TestTaskService:
    """Tests for TaskService."""

    def test_create_task(self, service):
        task = service.create_task(
            title="New Task",
            description="Description",
            priority=Priority.HIGH,
            category="Work",
        )

        assert task.id is not None
        assert task.title == "New Task"
        assert task.priority == Priority.HIGH

    def test_create_task_with_due_date(self, service):
        future = datetime.now() + timedelta(days=7)
        task = service.create_task(title="Future task", due_date=future)

        assert task.due_date is not None

    def test_create_task_past_due_date_raises(self, service):
        past = datetime.now() - timedelta(days=1)

        with pytest.raises(ValueError, match="past"):
            service.create_task(title="Past task", due_date=past)

    def test_get_task(self, service):
        created = service.create_task(title="Test")
        retrieved = service.get_task(created.id)

        assert retrieved.title == "Test"

    def test_get_task_not_found(self, service):
        with pytest.raises(TaskNotFoundError):
            service.get_task(999)

    def test_list_tasks_empty(self, service):
        tasks = service.list_tasks()
        assert tasks == []

    def test_list_tasks(self, service):
        service.create_task(title="Task 1")
        service.create_task(title="Task 2")

        tasks = service.list_tasks()
        assert len(tasks) == 2

    def test_list_tasks_sorted(self, service):
        service.create_task(title="Low", priority=Priority.LOW)
        service.create_task(title="High", priority=Priority.HIGH)

        tasks = service.list_tasks(sort_by="priority")
        assert tasks[0].title == "High"

    def test_update_task(self, service):
        task = service.create_task(title="Original")
        updated = service.update_task(task.id, title="Updated")

        assert updated.title == "Updated"

        # Verify persisted
        retrieved = service.get_task(task.id)
        assert retrieved.title == "Updated"

    def test_update_task_not_found(self, service):
        with pytest.raises(TaskNotFoundError):
            service.update_task(999, title="Ghost")

    def test_update_task_past_due_date_raises(self, service):
        task = service.create_task(title="Test")
        past = datetime.now() - timedelta(days=1)

        with pytest.raises(ValueError, match="past"):
            service.update_task(task.id, due_date=past)

    def test_delete_task(self, service):
        task = service.create_task(title="To delete")
        service.delete_task(task.id)

        with pytest.raises(TaskNotFoundError):
            service.get_task(task.id)

    def test_delete_task_not_found(self, service):
        with pytest.raises(TaskNotFoundError):
            service.delete_task(999)

    def test_toggle_completed(self, service):
        task = service.create_task(title="Toggle me")
        assert task.is_completed is False

        toggled = service.toggle_completed(task.id)
        assert toggled.is_completed is True

        # Verify persisted
        retrieved = service.get_task(task.id)
        assert retrieved.is_completed is True

        # Toggle back
        toggled_back = service.toggle_completed(task.id)
        assert toggled_back.is_completed is False

    def test_toggle_completed_not_found(self, service):
        with pytest.raises(TaskNotFoundError):
            service.toggle_completed(999)

    def test_search_by_priority(self, service):
        service.create_task(title="High 1", priority=Priority.HIGH)
        service.create_task(title="Low 1", priority=Priority.LOW)

        results = service.search_by_priority(Priority.HIGH)
        assert len(results) == 1
        assert results[0].title == "High 1"

    def test_search_by_category(self, service):
        service.create_task(title="Work task", category="Work")
        service.create_task(title="Home task", category="Home")

        results = service.search_by_category("Work")
        assert len(results) == 1
        assert results[0].title == "Work task"

    def test_search_by_date_range(self, service):
        now = datetime.now()
        service.create_task(
            title="This week",
            due_date=now + timedelta(days=3),
        )
        service.create_task(
            title="Next month",
            due_date=now + timedelta(days=45),
        )

        results = service.search_by_date_range(
            "due_date",
            now,
            now + timedelta(days=7),
        )
        assert len(results) == 1
        assert results[0].title == "This week"

    def test_search_by_date_range_invalid(self, service):
        now = datetime.now()

        with pytest.raises(ValueError, match="Start date must be before"):
            service.search_by_date_range(
                "due_date",
                now + timedelta(days=7),
                now,
            )
