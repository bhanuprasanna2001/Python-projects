"""Tests for TaskRepository."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from task_manager.models import Priority, Task
from task_manager.repository import TaskRepository


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def repository(temp_db):
    """Create a repository with a temporary database."""
    return TaskRepository(temp_db)


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        title="Test Task",
        description="A test task",
        priority=Priority.HIGH,
        due_date=datetime(2026, 12, 31, 23, 59),
        category="Testing",
    )


class TestTaskRepository:
    """Tests for TaskRepository."""

    def test_create_and_retrieve(self, repository, sample_task):
        created = repository.create(sample_task)

        assert created.id is not None
        assert created.title == sample_task.title
        assert created.created_at is not None

        retrieved = repository.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.title == sample_task.title

    def test_get_by_id_not_found(self, repository):
        assert repository.get_by_id(999) is None

    def test_get_all_empty(self, repository):
        tasks = repository.get_all()
        assert tasks == []

    def test_get_all_multiple(self, repository):
        repository.create(Task(title="Task 1"))
        repository.create(Task(title="Task 2"))
        repository.create(Task(title="Task 3"))

        tasks = repository.get_all()
        assert len(tasks) == 3
        assert [t.title for t in tasks] == ["Task 1", "Task 2", "Task 3"]

    def test_update(self, repository, sample_task):
        created = repository.create(sample_task)
        updated = created.with_updates(title="Updated Title")

        result = repository.update(updated)
        assert result is True

        retrieved = repository.get_by_id(created.id)
        assert retrieved.title == "Updated Title"

    def test_update_not_found(self, repository):
        task = Task(title="Ghost", id=999)
        assert repository.update(task) is False

    def test_delete(self, repository, sample_task):
        created = repository.create(sample_task)

        result = repository.delete(created.id)
        assert result is True
        assert repository.get_by_id(created.id) is None

    def test_delete_not_found(self, repository):
        assert repository.delete(999) is False

    def test_find_by_priority(self, repository):
        repository.create(Task(title="High 1", priority=Priority.HIGH))
        repository.create(Task(title="Low 1", priority=Priority.LOW))
        repository.create(Task(title="High 2", priority=Priority.HIGH))

        high_tasks = repository.find_by_priority(Priority.HIGH)
        assert len(high_tasks) == 2
        assert all(t.priority == Priority.HIGH for t in high_tasks)

    def test_find_by_category(self, repository):
        repository.create(Task(title="Work 1", category="Work"))
        repository.create(Task(title="Personal", category="Personal"))
        repository.create(Task(title="Work 2", category="Work"))

        work_tasks = repository.find_by_category("Work")
        assert len(work_tasks) == 2
        assert all(t.category == "Work" for t in work_tasks)

    def test_find_by_date_range(self, repository):
        repository.create(Task(title="Early", due_date=datetime(2026, 1, 1, 10, 0)))
        repository.create(Task(title="Middle", due_date=datetime(2026, 6, 15, 10, 0)))
        repository.create(Task(title="Late", due_date=datetime(2026, 12, 31, 10, 0)))

        mid_year = repository.find_by_date_range(
            "due_date",
            datetime(2026, 3, 1, 0, 0),
            datetime(2026, 9, 30, 23, 59),
        )
        assert len(mid_year) == 1
        assert mid_year[0].title == "Middle"

    def test_get_sorted_by_priority(self, repository):
        repository.create(Task(title="Low", priority=Priority.LOW))
        repository.create(Task(title="High", priority=Priority.HIGH))
        repository.create(Task(title="Medium", priority=Priority.MEDIUM))

        sorted_tasks = repository.get_sorted("priority")
        priorities = [t.priority for t in sorted_tasks]
        assert priorities == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def test_get_sorted_invalid_field(self, repository):
        with pytest.raises(ValueError, match="Invalid sort field"):
            repository.get_sorted("invalid")

    def test_find_by_date_range_invalid_field(self, repository):
        with pytest.raises(ValueError, match="Invalid date field"):
            repository.find_by_date_range("invalid", datetime.now(), datetime.now())
