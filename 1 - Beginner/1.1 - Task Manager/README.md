# Task Manager

A CLI task management application with SQLite persistence.

## Features

- Create, read, update, delete tasks
- Toggle task completion status
- Search by priority, category, or date range
- Sort by due date, priority, or creation time
- Persistent SQLite storage

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Create a task
python -m task_manager create "Review PR" --priority HIGH --due "2026-01-10 14:00" --category Work

# List all tasks
python -m task_manager list

# Update a task
python -m task_manager update 1

# Delete a task
python -m task_manager delete 1

# Toggle completion
python -m task_manager toggle 1

# Search tasks
python -m task_manager search --priority HIGH
python -m task_manager search --category Work
python -m task_manager search --from "2026-01-01 00:00" --to "2026-01-31 23:59"

# Sort tasks
python -m task_manager list --sort-by priority
python -m task_manager list --sort-by due_date
```

## Project Structure

```
ref_tm/
├── task_manager/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── cli.py           # Argument parsing
│   ├── models.py        # Task dataclass
│   ├── repository.py    # Database operations
│   ├── service.py       # Business logic
│   └── display.py       # Output formatting
├── tests/
│   ├── __init__.py
│   ├── Figuring out
│   ├── Figuring out
│   └── Figuring out
├── requirements.txt
└── README.md
```

## Design Principles

- **Single Responsibility**: Each module has one clear purpose
- **Dependency Injection**: Repository injected into service for testability
- **Type Safety**: Full type hints throughout
- **Immutable Data**: Task model uses frozen dataclass
- **Clean Interfaces**: Clear boundaries between layers
