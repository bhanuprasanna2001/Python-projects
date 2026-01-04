# 1.1 Task Manager

A CLI-based Task Manager built with Python and SQLite.

## Features

### Core Functionality (CRUD Operations)
- **Create** - Add new tasks with title, description, priority, due date, and category
- **Read** - List all tasks with formatted output
- **Update** - Modify existing tasks
- **Delete** - Remove tasks by ID
- **Toggle Complete** - Mark tasks as complete/incomplete

### Features
- **Priority Levels**: HIGH, MEDIUM, LOW
- **Due Dates**: Set deadlines with datetime support
- **Categories**: Organize tasks (Work, Personal, Academic, etc.)
- **Search**: Filter by priority, category, or date range
- **Sort**: Order tasks by priority, due date, or creation date

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Create a Task
```bash
python main.py -c "Complete project" -p HIGH -dd "2026-01-15 10:00" -cat "Work"
```

### List All Tasks
```bash
python main.py -l
```

### Update a Task
```bash
python main.py -u 1
```

### Delete a Task
```bash
python main.py -d 1
```

### Toggle Task Completion
```bash
python main.py -ic 1
```

### Search Tasks
```bash
python main.py -s
```

### Sort Tasks
```bash
python main.py -so
```

## Testing

Run all tests:
```bash
pytest test_task_manager.py -v
```

Run with coverage:
```bash
pytest test_task_manager.py --cov=src
```

Run specific tests:
```bash
pytest test_task_manager.py -k "toggle"
```

## Project Structure

```
1.1 - Task Manager/
├── main.py                 # Entry point with CLI argument parsing
├── src/
│   ├── task_manager.py    # TaskManager class with all operations
│   └── utils.py           # Helper functions and validation
├── tasks/
│   └── task_manager.db    # SQLite database (auto-created)
├── test_task_manager.py   # Comprehensive test suite
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore patterns
└── README.md             # This file
```

## Development Journey

### Goals Achieved

✅ **First Goal**: CRUD operations  
✅ **Second Goal**: Migrated from JSON to SQLite  
✅ **Third Goal**: Error handling, input validation, CLI interface  
✅ **Fourth Goal**: Priority levels, due dates, categories, search, sort  
✅ **Fifth Goal**: Comprehensive test suite with pytest

## Code Quality Improvements

- ✅ Fixed SQL injection vulnerabilities (using parameterized queries)
- ✅ Added docstrings to all methods
- ✅ Removed commented-out code
- ✅ Added input validation helpers
- ✅ Cleaned up unused imports
- ✅ Added requirements.txt and .gitignore
- ✅ Comprehensive test coverage including toggle_completed
