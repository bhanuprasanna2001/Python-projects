"""Command-line interface for task manager."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from task_manager.display import format_task_detail, format_tasks_table
from task_manager.models import Priority, Task
from task_manager.repository import TaskRepository
from task_manager.service import TaskNotFoundError, TaskService


def parse_datetime(value: str) -> datetime:
    """Parse datetime from string."""
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime format: '{value}'. Use: YYYY-MM-DD HH:MM"
        )


def parse_priority(value: str) -> Priority:
    """Parse priority from string."""
    try:
        return Priority.from_string(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="task_manager",
        description="A clean CLI task management application.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("title", help="Task title")
    create_parser.add_argument("-d", "--description", default="", help="Task description")
    create_parser.add_argument(
        "-p", "--priority", type=parse_priority, default=Priority.MEDIUM,
        help="Priority: LOW, MEDIUM, HIGH (default: MEDIUM)"
    )
    create_parser.add_argument(
        "--due", type=parse_datetime, help="Due date (YYYY-MM-DD HH:MM)"
    )
    create_parser.add_argument("-c", "--category", default="", help="Task category")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all tasks")
    list_parser.add_argument(
        "-s", "--sort-by", choices=["priority", "due_date", "created_at"],
        help="Sort tasks by field"
    )
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show task details")
    show_parser.add_argument("id", type=int, help="Task ID")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update a task")
    update_parser.add_argument("id", type=int, help="Task ID")
    update_parser.add_argument("-t", "--title", help="New title")
    update_parser.add_argument("-d", "--description", help="New description")
    update_parser.add_argument("-p", "--priority", type=parse_priority, help="New priority")
    update_parser.add_argument("--due", type=parse_datetime, help="New due date")
    update_parser.add_argument("-c", "--category", help="New category")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("id", type=int, help="Task ID")
    
    # Toggle command
    toggle_parser = subparsers.add_parser("toggle", help="Toggle task completion")
    toggle_parser.add_argument("id", type=int, help="Task ID")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search tasks")
    search_group = search_parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument("-p", "--priority", type=parse_priority, help="Search by priority")
    search_group.add_argument("-c", "--category", help="Search by category")
    search_group.add_argument("--date-field", choices=["due_date", "created_at"],
                              help="Search by date range (requires --from and --to)")
    search_parser.add_argument("--from", dest="from_date", type=parse_datetime,
                               help="Start date for range search")
    search_parser.add_argument("--to", dest="to_date", type=parse_datetime,
                               help="End date for range search")
    
    return parser


class CLI:
    """Command-line interface handler."""
    
    def __init__(self, service: TaskService) -> None:
        """Initialize CLI with a task service."""
        self._service = service
    
    def run(self, args: argparse.Namespace) -> int:
        """Execute the requested command. Returns exit code."""
        if args.command is None:
            print("No command specified. Use --help for usage.")
            return 1
        
        try:
            handler = getattr(self, f"_handle_{args.command}", None)
            if handler:
                handler(args)
                return 0
        except TaskNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except ValueError as e:
            print(f"Validation error: {e}")
            return 1
        
        return 1
    
    def _handle_create(self, args: argparse.Namespace) -> None:
        """Handle create command."""
        task = self._service.create_task(
            title=args.title,
            description=args.description,
            priority=args.priority,
            due_date=args.due,
            category=args.category,
        )
        print(f"Created task #{task.id}: {task.title}")
    
    def _handle_list(self, args: argparse.Namespace) -> None:
        """Handle list command."""
        tasks = self._service.list_tasks(sort_by=args.sort_by)
        print(format_tasks_table(tasks))
    
    def _handle_show(self, args: argparse.Namespace) -> None:
        """Handle show command."""
        task = self._service.get_task(args.id)
        print(format_task_detail(task))
    
    def _handle_update(self, args: argparse.Namespace) -> None:
        """Handle update command."""
        task = self._service.update_task(
            task_id=args.id,
            title=args.title,
            description=args.description,
            priority=args.priority,
            due_date=args.due,
            category=args.category,
        )
        print(f"Updated task #{task.id}")
    
    def _handle_delete(self, args: argparse.Namespace) -> None:
        """Handle delete command."""
        self._service.delete_task(args.id)
        print(f"Deleted task #{args.id}")
    
    def _handle_toggle(self, args: argparse.Namespace) -> None:
        """Handle toggle command."""
        task = self._service.toggle_completed(args.id)
        status = "completed" if task.is_completed else "not completed"
        print(f"Task #{task.id} marked as {status}")
    
    def _handle_search(self, args: argparse.Namespace) -> None:
        """Handle search command."""
        if args.priority:
            tasks = self._service.search_by_priority(args.priority)
        elif args.category:
            tasks = self._service.search_by_category(args.category)
        elif args.date_field:
            if not args.from_date or not args.to_date:
                print("Error: --from and --to are required for date range search")
                return
            tasks = self._service.search_by_date_range(
                args.date_field, args.from_date, args.to_date
            )
        else:
            tasks = []
        
        print(format_tasks_table(tasks))


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Initialize components
    db_path = Path(__file__).parent.parent / "data" / "task_manager.db"
    repository = TaskRepository(db_path)
    service = TaskService(repository)
    cli = CLI(service)
    
    return cli.run(args)
