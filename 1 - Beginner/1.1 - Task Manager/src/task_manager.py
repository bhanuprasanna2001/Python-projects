import sqlite3
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

# Database column indices (based on schema order)
TASK_ID = 0
TITLE = 1
DESCRIPTION = 2
IS_COMPLETED = 3
CREATED_AT = 4
PRIORITY = 5
DUE_DATE = 6
CATEGORY = 7

# Column headers for display
TABLE_HEADERS = ["task_id", "title", "description", "is_completed", "created_at", "priority", "due_date", "category"]


class TaskManager:
    """Manages tasks in a SQLite database with CRUD operations."""
    
    def connect_to_database(self, path: Path) -> bool:
        """Connect to SQLite database at given path."""
        try:
            self.conn = sqlite3.connect(path)
            self.cur = self.conn.cursor()
        except Exception as e:
            print(f"Couldn't connect to database: {e}")
            return False
        return True
    
    def commit_and_close_transaction(self) -> bool:
        """Commit changes and close database connection."""
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            print(f"Couldn't commit and close transaction: {e}")
            return False
        return True
    
    def create_database(self) -> bool:
        """Create Task_Manager table if it doesn't exist."""
        try:
            self.cur.execute(
                """
                    CREATE TABLE IF NOT EXISTS Task_Manager(
                        task_id INTEGER PRIMARY KEY,
                        title TEXT,
                        description TEXT,
                        is_completed BOOLEAN,
                        created_at TIMESTAMP,
                        priority VARCHAR(30),
                        due_date TIMESTAMP,
                        category TEXT
                    )
                """
            )
        except Exception as e:
            print(f"Couldn't create table: {e}")
            return False
        return True
    
    def create_task(self, task: str, priority: str, due_date: str, category: str) -> bool:
        """Create a new task with title, priority, due_date, and category."""
        try:
            description = input(f"Description for the task {task}: ")
            created_at = datetime.now()
            insert_query = """INSERT INTO Task_Manager (title, description, created_at, priority, due_date, category) VALUES(?, ?, ?, ?, ?, ?);"""
            self.cur.execute(insert_query, (task, description, created_at, priority, due_date, category))
        except Exception as e:
            print(f"Couldn't create task: {e}")
            return False
        return True
    
    def list_tasks(self, custom_query=None):
        """List all tasks or tasks matching custom SQL query."""
        try:
            if custom_query is None:
                list_query = """SELECT * FROM Task_Manager;"""
                self.cur.execute(list_query)
            else:
                self.cur.execute(custom_query)
                
            output = self.cur.fetchall()
            task_list = []
            for row in output:
                task_list.append(row)
            print(tabulate(task_list, headers=TABLE_HEADERS, tablefmt="psql"))
        except Exception as e:
            print(f"Couldn't list tasks: {e}")
            return False
        return True
    
    def update_tasks(self, id: str) -> bool:
        """Update task fields by task ID."""
        try:
            task = list(self.cur.execute("SELECT * FROM Task_Manager WHERE task_id=?;", (id,)).fetchone())
            if len(task):
                print(task)
                title_input = input(f"Update task {id}, {task[TITLE]} with Task Title (leave empty if no change): ")
                if title_input != "":
                    task[TITLE] = title_input
                
                description_input = input(f"Update task {id}, {task[DESCRIPTION]} with Task Description (leave empty if no change): ")
                if description_input != "":
                    task[DESCRIPTION] = description_input
                    
                priority_input = input(f"Update task {id}, {task[PRIORITY]} with Task Priority [LOW, MEDIUM, HIGH] (leave empty if no change): ")
                if priority_input != "":
                    if priority_input in ["LOW", "MEDIUM", "HIGH"]:
                        task[PRIORITY] = priority_input
                    else:
                        raise Exception("Update failed because Priority input not in Priority Levels.")
                
                due_date_input = input(f"Update task {id}, {task[DUE_DATE]} with Due Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 (leave empty if no change): ")
                if due_date_input != "":
                    due_date_obj = datetime.strptime(due_date_input, "%Y-%m-%d %H:%M")
                    if due_date_obj < datetime.now():
                        raise Exception("Arg Due Date is in the past, set a future date.")
                    task[DUE_DATE] = due_date_obj
                
                category_input = input(f"Update task {id}, {task[CATEGORY]} with Category (leave empty if no change): ")
                if category_input != "":
                    task[CATEGORY] = category_input
                    
                update_query = """UPDATE Task_Manager SET title=?, description=?, priority=?, due_date=?, category=? WHERE task_id=?;"""
                self.cur.execute(update_query, (task[TITLE], task[DESCRIPTION], task[PRIORITY], task[DUE_DATE], task[CATEGORY], task[TASK_ID]))
            else:
                raise Exception("ID not in Tasks, check the list of tasks.")
            
        except Exception as e:
            print(f"Couldn't update Task: {e}")
            return False
        return True
    
    def delete_tasks(self, id: str) -> bool:
        """Delete task by task ID."""
        try:
            task = list(self.cur.execute("SELECT * FROM Task_Manager WHERE task_id=?;", (id,)).fetchone())
            print(task)
            if len(task):
                delete_query = "DELETE FROM Task_Manager WHERE task_id=?;"
                self.cur.execute(delete_query, (task[TASK_ID],))
            else:
                raise Exception("ID not in Tasks, check the list of tasks.")
        except Exception as e:
            print(f"Couldn't delete Task: {e}")
            return False
        return True
    
    def search_tasks(self) -> bool:
        """Search tasks by priority, category, or date range."""
        try:
            selected_tasks = dict()
            search_strategy = input("Search Strategy (due_date, priority, category, created_at): ")
            if search_strategy in ["due_date", "priority", "category", "created_at"]:
                if search_strategy in ["due_date", "created_at"]:
                    from_date_input = datetime.strptime(input(f"{search_strategy.capitalize()} - From Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 : "), "%Y-%m-%d %H:%M")
                    to_date_input = datetime.strptime(input(f"{search_strategy.capitalize()} - To Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 : "), "%Y-%m-%d %H:%M")
                    search_query = f"SELECT * FROM Task_Manager WHERE {search_strategy} >= ? AND {search_strategy} <= ?;"
                    self.cur.execute(search_query, (from_date_input, to_date_input))
                    results = self.cur.fetchall()
                    task_list = []
                    for row in results:
                        task_list.append(row)
                    print(tabulate(task_list, headers=TABLE_HEADERS, tablefmt="psql"))
                    return True
                            
                elif search_strategy == "priority":
                    priority_input = input(f"Task Priority [LOW, MEDIUM, HIGH] to search: ")
                    if priority_input not in ["LOW", "MEDIUM", "HIGH"]:
                        raise Exception("Priority Input not in Priority Levels.")
                    search_query = "SELECT * FROM Task_Manager WHERE priority = ?;"
                    self.cur.execute(search_query, (priority_input,))
                    results = self.cur.fetchall()
                    task_list = []
                    for row in results:
                        task_list.append(row)
                    print(tabulate(task_list, headers=TABLE_HEADERS, tablefmt="psql"))
                    return True
                            
                elif search_strategy == "category":
                    category_input = input(f"Task Category to search: ")
                    search_query = "SELECT * FROM Task_Manager WHERE category = ?;"
                    self.cur.execute(search_query, (category_input,))
                    results = self.cur.fetchall()
                    task_list = []
                    for row in results:
                        task_list.append(row)
                    print(tabulate(task_list, headers=TABLE_HEADERS, tablefmt="psql"))
                    return True
            else:
                raise Exception("Input Search Strategy not in Strategies list.")
            
        except Exception as e:
            print(f"Couldn't search: {e}")
            return False
        return True
    
    def sort_tasks(self) -> bool:
        """Sort tasks by due_date, priority, or created_at."""
        try:
            selected_tasks = dict()
            sort_strategy = input("Search Strategy (due_date, priority, created_at): ")
            if sort_strategy in ["due_date", "priority", "created_at"]:
                if sort_strategy in ["due_date", "created_at"]:
                    sort_query = f"SELECT * FROM Task_Manager ORDER BY {sort_strategy} ASC;"
                    print(sort_query)
                            
                elif sort_strategy == "priority":
                    sort_query = f"SELECT * FROM Task_Manager ORDER BY CASE WHEN priority = 'HIGH' THEN 1 WHEN priority = 'MEDIUM' THEN 2 WHEN priority = 'LOW' THEN 3 END ASC, due_date;"
                    print(sort_query)
                            
                self.list_tasks(custom_query=sort_query)
            else:
                raise Exception("Input Search Strategy not in Strategies list.")
            
        except Exception as e:
            print(f"Couldn't Sort: {e}")
            return False
        return True
    
    def toggle_completed(self, id: str) -> bool:
        """Toggle the is_completed status of a task."""
        try:
            task = list(self.cur.execute("SELECT * FROM Task_Manager WHERE task_id=?;", (id,)).fetchone())
            if len(task):
                current_status = task[IS_COMPLETED]
                new_status = not current_status
                update_query = """UPDATE Task_Manager SET is_completed=? WHERE task_id=?;"""
                self.cur.execute(update_query, (new_status, task[TASK_ID]))
                print(f"Task {id} completion status toggled to: {new_status}")
            else:
                raise Exception("ID not in Tasks, check the list of tasks.")
        except Exception as e:
            print(f"Couldn't toggle completion status: {e}")
            return False
        return True