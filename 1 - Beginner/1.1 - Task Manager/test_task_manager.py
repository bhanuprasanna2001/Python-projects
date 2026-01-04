"""
Unit tests for Task Manager Application

Testing Strategy:
1. CRUD Operations (Create, Read, Update, Delete)
2. Search Operations (by priority, category, dates)
3. Sort Operations (by priority, due_date, created_at)
4. Edge Cases (empty results, invalid inputs)

Framework: pytest
Run with: pytest test_task_manager.py -v
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from src.task_manager import TaskManager


# ============================================================================
# FIXTURES - Setup/Teardown for Tests
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing, clean up after test."""
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    db_path = Path(temp_file.name)
    temp_file.close()
    
    yield db_path  # Provide path to test
    
    # Cleanup: remove temp file after test
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def task_manager(temp_db):
    """Create TaskManager instance with temp database."""
    tm = TaskManager()
    tm.connect_to_database(temp_db)
    tm.create_database()
    return tm


@pytest.fixture
def populated_db(task_manager):
    """Create TaskManager with sample test data."""
    # Add diverse test tasks
    test_tasks = [
        ("High Priority Task", "HIGH", "2026-01-10 10:00", "Work"),
        ("Medium Task 1", "MEDIUM", "2026-01-15 14:00", "Personal"),
        ("Low Priority Task", "LOW", "2026-01-20 16:00", "Work"),
        ("High Academic Task", "HIGH", "2026-01-08 09:00", "Academic"),
        ("Medium Task 2", "MEDIUM", "2026-01-12 11:00", "Personal"),
    ]
    
    for title, priority, due_date, category in test_tasks:
        # Simulate user input for description
        import io
        import sys
        sys.stdin = io.StringIO(f"Description for {title}\n")
        
        # Insert using parameterized query directly to avoid input prompt
        created_at = datetime.now()
        task_manager.cur.execute(
            "INSERT INTO Task_Manager (title, description, created_at, priority, due_date, category) VALUES(?, ?, ?, ?, ?, ?);",
            (title, f"Description for {title}", created_at, priority, due_date, category)
        )
    
    task_manager.conn.commit()
    return task_manager


# ============================================================================
# DATABASE CONNECTION & SETUP TESTS
# ============================================================================

def test_database_connection(temp_db):
    """Test: Can connect to database successfully."""
    tm = TaskManager()
    result = tm.connect_to_database(temp_db)
    assert result == True
    assert tm.conn is not None
    tm.conn.close()


def test_database_creation(task_manager):
    """Test: Database table is created with correct schema."""
    result = task_manager.create_database()
    assert result == True
    
    # Verify table exists with correct columns
    task_manager.cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Task_Manager';")
    assert task_manager.cur.fetchone() is not None


# ============================================================================
# CREATE TESTS
# ============================================================================

def test_create_task(task_manager, monkeypatch):
    """Test: Can create a new task successfully."""
    # Mock user input for description
    monkeypatch.setattr('builtins.input', lambda _: "Test task description")
    
    result = task_manager.create_task("Test Task", "HIGH", "2026-01-15 10:00", "Testing")
    assert result == True
    
    # Verify task was inserted
    task_manager.cur.execute("SELECT COUNT(*) FROM Task_Manager WHERE title='Test Task';")
    count = task_manager.cur.fetchone()[0]
    assert count == 1


def test_create_task_with_all_priorities(task_manager, monkeypatch):
    """Test: Can create tasks with all priority levels."""
    monkeypatch.setattr('builtins.input', lambda _: "Test description")
    
    for priority in ["HIGH", "MEDIUM", "LOW"]:
        result = task_manager.create_task(f"Task {priority}", priority, "2026-01-15 10:00", "Test")
        assert result == True
    
    # Verify all three were created
    task_manager.cur.execute("SELECT COUNT(*) FROM Task_Manager;")
    assert task_manager.cur.fetchone()[0] == 3


# ============================================================================
# READ/LIST TESTS
# ============================================================================

def test_list_tasks_empty_database(task_manager, capsys):
    """Test: Listing tasks in empty database shows empty table."""
    result = task_manager.list_tasks()
    assert result == True
    
    captured = capsys.readouterr()
    assert "task_id" in captured.out  # Header should still show


def test_list_tasks_with_data(populated_db, capsys):
    """Test: Listing tasks shows all tasks correctly."""
    result = populated_db.list_tasks()
    assert result == True
    
    captured = capsys.readouterr()
    # Check that all test tasks appear
    assert "High Priority Task" in captured.out
    assert "Medium Task 1" in captured.out
    assert "Low Priority Task" in captured.out


# ============================================================================
# UPDATE TESTS
# ============================================================================

def test_update_task(populated_db, monkeypatch):
    """Test: Can update an existing task's fields."""
    # Setup: Mock user inputs (new title, new description, skip others)
    inputs = iter(["Updated Title", "Updated Description", "", "", ""])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    
    result = populated_db.update_tasks("1")
    assert result == True
    
    # Verify update
    populated_db.cur.execute("SELECT title, description FROM Task_Manager WHERE task_id=1;")
    title, desc = populated_db.cur.fetchone()
    assert title == "Updated Title"
    assert desc == "Updated Description"


def test_update_nonexistent_task(populated_db, monkeypatch):
    """Test: Updating non-existent task fails gracefully."""
    monkeypatch.setattr('builtins.input', lambda _: "")
    
    # Try to update task ID 999 (doesn't exist) - should return False
    result = populated_db.update_tasks("999")
    assert result == False


# ============================================================================
# DELETE TESTS
# ============================================================================

def test_delete_task(populated_db):
    """Test: Can delete an existing task."""
    # Verify task exists first
    populated_db.cur.execute("SELECT COUNT(*) FROM Task_Manager WHERE task_id=1;")
    assert populated_db.cur.fetchone()[0] == 1
    
    result = populated_db.delete_tasks("1")
    assert result == True
    
    # Verify task is deleted
    populated_db.cur.execute("SELECT COUNT(*) FROM Task_Manager WHERE task_id=1;")
    assert populated_db.cur.fetchone()[0] == 0


def test_delete_all_tasks(populated_db):
    """Test: Can delete multiple tasks sequentially."""
    # Count initial tasks
    populated_db.cur.execute("SELECT COUNT(*) FROM Task_Manager;")
    initial_count = populated_db.cur.fetchone()[0]
    assert initial_count == 5
    
    # Delete first 3 tasks
    for task_id in ["1", "2", "3"]:
        populated_db.delete_tasks(task_id)
    
    # Verify only 2 remain
    populated_db.cur.execute("SELECT COUNT(*) FROM Task_Manager;")
    assert populated_db.cur.fetchone()[0] == 2


# ============================================================================
# SEARCH TESTS - By Priority
# ============================================================================

@pytest.mark.parametrize("priority,expected_count", [
    ("HIGH", 2),
    ("MEDIUM", 2),
    ("LOW", 1),
])
def test_search_by_priority(populated_db, priority, expected_count):
    """Test: Search by priority returns correct number of tasks."""
    search_query = f"SELECT * FROM Task_Manager WHERE priority = '{priority}';"
    populated_db.cur.execute(search_query)
    results = populated_db.cur.fetchall()
    assert len(results) == expected_count


def test_search_by_priority_no_results(populated_db):
    """Test: Search for non-existent priority returns empty."""
    # We only have HIGH, MEDIUM, LOW - searching for something else
    search_query = "SELECT * FROM Task_Manager WHERE priority = 'URGENT';"
    populated_db.cur.execute(search_query)
    results = populated_db.cur.fetchall()
    assert len(results) == 0


# ============================================================================
# SEARCH TESTS - By Category
# ============================================================================

@pytest.mark.parametrize("category,expected_count", [
    ("Work", 2),
    ("Personal", 2),
    ("Academic", 1),
])
def test_search_by_category(populated_db, category, expected_count):
    """Test: Search by category returns correct tasks."""
    search_query = f"SELECT * FROM Task_Manager WHERE category = '{category}';"
    populated_db.cur.execute(search_query)
    results = populated_db.cur.fetchall()
    assert len(results) == expected_count


def test_search_by_category_case_sensitive(populated_db):
    """Test: Category search is case-sensitive."""
    # Search for lowercase 'work' should return 0 (we stored 'Work')
    search_query = "SELECT * FROM Task_Manager WHERE category = 'work';"
    populated_db.cur.execute(search_query)
    results = populated_db.cur.fetchall()
    assert len(results) == 0


# ============================================================================
# SEARCH TESTS - By Date Range
# ============================================================================

def test_search_by_due_date_range(populated_db):
    """Test: Search by due_date range returns correct tasks."""
    # Search for tasks due between Jan 1-10, 2026
    search_query = "SELECT * FROM Task_Manager WHERE due_date >= '2026-01-01 00:00:00' AND due_date <= '2026-01-10 23:59:59';"
    populated_db.cur.execute(search_query)
    results = populated_db.cur.fetchall()
    
    # Should return: High Priority Task (Jan 10) and High Academic Task (Jan 8)
    assert len(results) == 2


def test_search_by_date_no_results(populated_db):
    """Test: Date range with no tasks returns empty."""
    # Search far in the future where we have no tasks
    search_query = "SELECT * FROM Task_Manager WHERE due_date >= '2027-01-01 00:00:00';"
    populated_db.cur.execute(search_query)
    results = populated_db.cur.fetchall()
    assert len(results) == 0


# ============================================================================
# SORT TESTS
# ============================================================================

def test_sort_by_priority(populated_db):
    """Test: Sorting by priority orders HIGH → MEDIUM → LOW."""
    sort_query = """
        SELECT priority FROM Task_Manager 
        ORDER BY CASE 
            WHEN priority = 'HIGH' THEN 1 
            WHEN priority = 'MEDIUM' THEN 2 
            WHEN priority = 'LOW' THEN 3 
        END ASC;
    """
    populated_db.cur.execute(sort_query)
    results = [row[0] for row in populated_db.cur.fetchall()]
    
    # First two should be HIGH, next two MEDIUM, last one LOW
    assert results[:2] == ["HIGH", "HIGH"]
    assert results[2:4] == ["MEDIUM", "MEDIUM"]
    assert results[4] == "LOW"


def test_sort_by_due_date_ascending(populated_db):
    """Test: Sorting by due_date shows earliest first."""
    sort_query = "SELECT due_date FROM Task_Manager ORDER BY due_date ASC;"
    populated_db.cur.execute(sort_query)
    results = [row[0] for row in populated_db.cur.fetchall()]
    
    # Verify dates are in ascending order
    assert results == sorted(results)


def test_sort_by_created_at(populated_db):
    """Test: Sorting by created_at orders chronologically."""
    sort_query = "SELECT created_at FROM Task_Manager ORDER BY created_at ASC;"
    populated_db.cur.execute(sort_query)
    results = [row[0] for row in populated_db.cur.fetchall()]
    
    # Should be in ascending order
    assert results == sorted(results)


# ============================================================================
# INTEGRATION TESTS - Multiple Operations
# ============================================================================

def test_create_search_update_delete_workflow(task_manager, monkeypatch):
    """Test: Complete workflow - Create → Search → Update → Delete."""
    # Step 1: Create
    monkeypatch.setattr('builtins.input', lambda _: "Integration test task")
    task_manager.create_task("Workflow Test", "HIGH", "2026-01-15 10:00", "Testing")
    
    # Step 2: Search and verify
    task_manager.cur.execute("SELECT * FROM Task_Manager WHERE title='Workflow Test';")
    task = task_manager.cur.fetchone()
    assert task is not None
    task_id = task[0]
    
    # Step 3: Update
    inputs = iter(["Updated in Workflow", "", "", "", ""])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    task_manager.update_tasks(str(task_id))
    
    task_manager.cur.execute("SELECT title FROM Task_Manager WHERE task_id=?;", (task_id,))
    updated_title = task_manager.cur.fetchone()[0]
    assert updated_title == "Updated in Workflow"
    
    # Step 4: Delete
    task_manager.delete_tasks(str(task_id))
    task_manager.cur.execute("SELECT * FROM Task_Manager WHERE task_id=?;", (task_id,))
    assert task_manager.cur.fetchone() is None


def test_bulk_operations(task_manager, monkeypatch):
    """Test: Can handle multiple tasks efficiently."""
    monkeypatch.setattr('builtins.input', lambda _: "Bulk test")
    
    # Create 10 tasks
    for i in range(10):
        priority = ["HIGH", "MEDIUM", "LOW"][i % 3]
        task_manager.create_task(f"Bulk Task {i}", priority, "2026-01-15 10:00", "Bulk")
    
    # Verify count
    task_manager.cur.execute("SELECT COUNT(*) FROM Task_Manager;")
    assert task_manager.cur.fetchone()[0] == 10


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

def test_commit_and_close(task_manager):
    """Test: Can commit and close transaction successfully."""
    result = task_manager.commit_and_close_transaction()
    assert result == True


def test_query_empty_database(task_manager):
    """Test: Queries on empty database don't crash."""
    task_manager.cur.execute("SELECT * FROM Task_Manager;")
    results = task_manager.cur.fetchall()
    assert results == []


def test_special_characters_in_task(task_manager, monkeypatch):
    """Test: Can handle special characters in task data."""
    monkeypatch.setattr('builtins.input', lambda _: "Description with 'quotes' and \"double quotes\"")
    
    result = task_manager.create_task(
        "Task with 'special' chars & symbols!",
        "HIGH",
        "2026-01-15 10:00",
        "Testing & QA"
    )
    assert result == True


# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================

if __name__ == "__main__":
    print("""
    Run tests with:
        pytest test_task_manager.py -v                  # Verbose output
        pytest test_task_manager.py -v --tb=short      # Short traceback
        pytest test_task_manager.py -k "search"        # Run only search tests
        pytest test_task_manager.py --cov=src          # With coverage report
    """)
