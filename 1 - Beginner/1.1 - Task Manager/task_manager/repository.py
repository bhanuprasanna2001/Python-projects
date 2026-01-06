"""SQLite repository for task persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from task_manager.models import Priority, Task


class TaskRepository:
    """Handles all database operations for tasks.

    This class follows the Repository pattern, providing a clean interface
    for data persistence while hiding SQLite implementation details.
    """

    _CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            priority TEXT NOT NULL,
            due_date TEXT,
            category TEXT DEFAULT ''
        )
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize repository with database path."""
        self._db_path = db_path
        self._ensure_directory()
        self._init_schema()

    def _ensure_directory(self) -> None:
        """Create database directory if needed."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._connection() as conn:
            conn.execute(self._CREATE_TABLE_SQL)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        due_date = None
        if row["due_date"]:
            due_date = datetime.fromisoformat(row["due_date"])

        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            is_completed=bool(row["is_completed"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            priority=Priority(row["priority"]),
            due_date=due_date,
            category=row["category"],
        )

    def create(self, task: Task) -> Task:
        """Insert a new task and return it with assigned ID."""
        created_at = task.created_at or datetime.now()
        due_date_str = task.due_date.isoformat() if task.due_date else None

        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks
                    (title, description, is_completed, created_at, priority, due_date, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.title,
                    task.description,
                    int(task.is_completed),
                    created_at.isoformat(),
                    task.priority.value,
                    due_date_str,
                    task.category,
                ),
            )
            new_id = cursor.lastrowid

        return Task(
            id=new_id,
            title=task.title,
            description=task.description,
            is_completed=task.is_completed,
            created_at=created_at,
            priority=task.priority,
            due_date=task.due_date,
            category=task.category,
        )

    def get_by_id(self, task_id: int) -> Task | None:
        """Retrieve a task by ID, or None if not found."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

        return self._row_to_task(row) if row else None

    def get_all(self) -> Sequence[Task]:
        """Retrieve all tasks."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        return [self._row_to_task(row) for row in rows]

    def update(self, task: Task) -> bool:
        """Update an existing task. Returns True if task was found and updated."""
        if task.id is None:
            return False

        due_date_str = task.due_date.isoformat() if task.due_date else None

        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, is_completed = ?,
                    priority = ?, due_date = ?, category = ?
                WHERE id = ?
                """,
                (
                    task.title,
                    task.description,
                    int(task.is_completed),
                    task.priority.value,
                    due_date_str,
                    task.category,
                    task.id,
                ),
            )
        return cursor.rowcount > 0

    def delete(self, task_id: int) -> bool:
        """Delete a task by ID. Returns True if task was found and deleted."""
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0

    def find_by_priority(self, priority: Priority) -> Sequence[Task]:
        """Find all tasks with given priority."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE priority = ? ORDER BY id",
                (priority.value,),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def find_by_category(self, category: str) -> Sequence[Task]:
        """Find all tasks with given category."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE category = ? ORDER BY id",
                (category,),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    # SQL query templates - using static strings eliminates SQL injection risk
    _QUERY_BY_DUE_DATE = (
        "SELECT * FROM tasks WHERE due_date >= ? AND due_date <= ? ORDER BY due_date"
    )
    _QUERY_BY_CREATED_AT = (
        "SELECT * FROM tasks WHERE created_at >= ? AND created_at <= ? ORDER BY created_at"
    )
    _QUERY_SORT_PRIORITY = """
        SELECT * FROM tasks ORDER BY
            CASE priority
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
            END, due_date
    """
    _QUERY_SORT_DUE_DATE = "SELECT * FROM tasks ORDER BY due_date"
    _QUERY_SORT_CREATED_AT = "SELECT * FROM tasks ORDER BY created_at"

    def find_by_date_range(self, field: str, start: datetime, end: datetime) -> Sequence[Task]:
        """Find tasks within a date range for given field."""
        queries = {
            "due_date": self._QUERY_BY_DUE_DATE,
            "created_at": self._QUERY_BY_CREATED_AT,
        }
        if field not in queries:
            raise ValueError(f"Invalid date field: {field}")

        with self._connection() as conn:
            rows = conn.execute(
                queries[field],
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_sorted(self, sort_by: str) -> Sequence[Task]:
        """Get all tasks sorted by specified field."""
        queries = {
            "priority": self._QUERY_SORT_PRIORITY,
            "due_date": self._QUERY_SORT_DUE_DATE,
            "created_at": self._QUERY_SORT_CREATED_AT,
        }
        if sort_by not in queries:
            raise ValueError(f"Invalid sort field: {sort_by}")

        with self._connection() as conn:
            rows = conn.execute(queries[sort_by]).fetchall()
        return [self._row_to_task(row) for row in rows]
