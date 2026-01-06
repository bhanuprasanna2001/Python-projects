"""Display formatting for task output."""

from collections.abc import Sequence
from datetime import datetime

from tabulate import tabulate

from task_manager.models import Task


def format_tasks_table(tasks: Sequence[Task]) -> str:
    """Format tasks as a table string."""
    if not tasks:
        return "No tasks found."

    headers = ["ID", "Title", "Done", "Priority", "Due Date", "Category", "Created"]
    rows = [
        [
            task.id,
            _truncate(task.title, 30),
            "✓" if task.is_completed else "",
            task.priority.value,
            _format_date(task.due_date),
            _truncate(task.category, 15),
            _format_date(task.created_at),
        ]
        for task in tasks
    ]
    return tabulate(rows, headers=headers, tablefmt="simple")


def format_task_detail(task: Task) -> str:
    """Format a single task with full details."""
    done = "Yes" if task.is_completed else "No"
    due = _format_date(task.due_date) or "Not set"
    created = _format_date(task.created_at) or "Unknown"

    return f"""
Task #{task.id}
{"─" * 40}
Title:       {task.title}
Description: {task.description or "(none)"}
Priority:    {task.priority.value}
Category:    {task.category or "(none)"}
Completed:   {done}
Due Date:    {due}
Created:     {created}
""".strip()


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _format_date(dt: datetime | None) -> str:
    """Format datetime for display."""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")
