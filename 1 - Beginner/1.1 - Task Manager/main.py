import argparse
from pathlib import Path
from datetime import datetime
from src.task_manager import TaskManager
from src.utils import (
    create_tasks_json_if_not_exists,
    validate_task_id,
    validate_priority
)

def create_argparse():
    parser = argparse.ArgumentParser(prog="Professional Task Manager", 
                                     description="Does CRUD operations and advanced selection for managing tasks.", 
                                     epilog="1.1 Project - Learning to Fail then to Succeed.")
    
    parser.add_argument("-c", "--create", type=str, help="Create a task")
    parser.add_argument("-l", "--list", help="List all tasks", action="store_true")
    parser.add_argument("-u", "--update", help="Update task when Id provided")
    parser.add_argument("-d", "--delete", help="Delete task when Id provided")
    parser.add_argument("-s", "--search", help="Search tasks", action="store_true")
    parser.add_argument("-so", "--sort", help="Sort tasks", action="store_true")
    parser.add_argument("-ic", "--is_completed", help="Task completed status change. ID Provide.")
    parser.add_argument("-p", "--priority", help="Priority level [LOW, MEDIUM, HIGH]")
    parser.add_argument("-dd", "--due_date", help="Due Date for the task, format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11")
    parser.add_argument("-cat", "--category", help='Category for the task. Eg "Study".')
    parser.add_argument("-i", "--interactive", help="Interactive version.", action="store_true")
    
    return parser

def validate_args(args: argparse.Namespace):
    try:
        if args.create is not None:
            if args.priority is None:
                raise Exception("Priority arg is missing")
            elif args.due_date is None:
                raise Exception("Due Date arg is missing")
            elif args.category is None:
                raise Exception("Category arg is missing")
        
        if args.priority is not None and not validate_priority(args.priority):
            raise Exception("Arg Priority not in Priority Levels.")

        if args.due_date is not None and datetime.strptime(args.due_date, "%Y-%m-%d %H:%M") < datetime.now():
            raise Exception("Arg Due Date is in the past, set a future date.")
        
        # Validate task IDs for operations that need them
        if args.update and not validate_task_id(args.update):
            raise Exception("Invalid task ID for update operation.")
        if args.delete and not validate_task_id(args.delete):
            raise Exception("Invalid task ID for delete operation.")
        if args.is_completed and not validate_task_id(args.is_completed):
            raise Exception("Invalid task ID for toggle completion operation.")
    except Exception as e:
        print(f"Args Validation Failed: {e}")
        return False
    return True

def main():
    args_parser = create_argparse()
    args = args_parser.parse_args()
    
    if not validate_args(args):
        return
    
    PROJECT_ROOT = Path(__file__).parent
    TASKS_SQL_PATH = PROJECT_ROOT / "tasks" / "task_manager.db"
    
    task_manager = TaskManager()
    
    ### SQLite3 Version
    
    # 1. Connect Database
    if task_manager.connect_to_database(TASKS_SQL_PATH):
        print("Successfuly Connected to Task_Manager!")
    else:
        raise Exception("Failed to connect!")
    
    # 2. Create Database
    if task_manager.create_database():
        print("Successfully created database!")
    else:
        raise Exception("Failed to create database!")
    
    # 3. If provided create task, then create task and insert to db
    if args.create is not None:
        if task_manager.create_task(args.create, args.priority, args.due_date, args.category):
            print("Successfully Created Task!")
        else:
            raise Exception("Failed to Create Task!")
    
    # 4. If asked to List tasks, list tasks
    if args.list:
        if task_manager.list_tasks():
            print("Succesfully Listed Tasks!")
        else:
            raise Exception("Failed to List Tasks!")
    
    # 5. If asked to update task based on ID, then update
    if args.update:
        if task_manager.update_tasks(args.update):
            print("Successfully Updated Tasks!")
        else:
            raise Exception("Failed to Update Tasks!")
    
    # 6. If asked to delete task based on ID, then delete
    if args.delete:
        if task_manager.delete_tasks(args.delete):
            print("Successfully Deleted Tasks!")
        else:
            raise Exception("Failed to Delete Tasks!")
    
    # 6. Search Tasks
    if args.search:
        if task_manager.search_tasks():
            print("Successfully Search completed!")
        else:
            raise Exception("Failed to Search!")
        
    # 7. Sort Tasks
    if args.sort:
        if task_manager.sort_tasks():
            print("Successfully Sort completed!")
        else:
            raise Exception("Failed to Sort!")
        
    # 8. Check Task Completed
    if args.is_completed:
        if task_manager.toggle_completed(args.is_completed):
            print("Successfully toggled task completion!")
        else:
            raise Exception("Failed to toggle task completion.")
        
    # 9. Commit and Close SQLite3 DB Transaction
    if task_manager.commit_and_close_transaction():
        print("Successfuly Commit and Closed the SQLite3 DB Transaction!")
    else:
        raise Exception(f"SQL Commit and Closing couldn't happen")
    
    
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error occured: {e}")