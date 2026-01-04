import os
import json
from pathlib import Path


def create_tasks_json_if_not_exists(path: Path):
    """Create an empty JSON file for tasks if it doesn't exist."""
    try:
        path.resolve()
        mode = "r" if path.exists() else "w"
        
        if mode == "r":
            return
        
        with open(path, mode) as fp:
            json.dump({}, fp)
    except Exception as e:
        print(f"Couldn't create tasks.json: {e}")


def check_json_empty(json) -> bool:
    """Check if JSON dictionary is empty."""
    return len(json) == 0


def check_id_exists_in_tasks(id, tasks) -> bool:
    """Check if task ID exists in tasks dictionary."""
    return id in tasks.keys()


def validate_task_id(task_id: str) -> bool:
    """Validate that task ID is a positive integer."""
    try:
        id_int = int(task_id)
        return id_int > 0
    except ValueError:
        return False


def validate_priority(priority: str) -> bool:
    """Validate priority is one of: HIGH, MEDIUM, LOW."""
    return priority in ["HIGH", "MEDIUM", "LOW"]


def validate_category(category: str) -> bool:
    """Validate category is not empty and reasonable length."""
    return len(category) > 0 and len(category) <= 50


def validate_title(title: str) -> bool:
    """Validate title is not empty and reasonable length."""
    return len(title) > 0 and len(title) <= 200


def validate_description(description: str) -> bool:
    """Validate description is reasonable length."""
    return len(description) <= 1000