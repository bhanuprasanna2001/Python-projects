import os
import json
import uuid
import pprint
import sqlite3
from pathlib import Path
from datetime import datetime
from tabulate import tabulate
from src.utils import (
    check_json_empty,
    check_id_exists_in_tasks
)

# First step is to get all the tasks in JSON.
# It seems that you can use r+ to do the dump because after the read 
# the pointer is at the end of the file, from which it starts to write
# leading to the issues.

class TaskManager:
    
    def connect_to_database(self, path: Path) -> bool:
        try:
            self.conn = sqlite3.connect(path)
            self.cur = self.conn.cursor()
        except Exception as e:
            print(f"Couldn't connect to database: {e}")
            return False
        return True
    
    def commit_and_close_transaction(self) -> bool:
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            print(f"Couldn't commit and close transaction: {e}")
            return False
        return True
    
    def create_database(self) -> bool:
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
        try:
            if custom_query == None:
                list_query = """SELECT * FROM Task_Manager;"""
                self.cur.execute(list_query)
            else:
                self.cur.execute(custom_query)
                
            output = self.cur.fetchall()
            task_list = []
            for row in output:
                task_list.append(row)
            print(tabulate(task_list, headers=["task_id", "title", "description", "created_at", "priority", "due_date", "category"], tablefmt="psql"))
        except Exception as e:
            print(f"Couldn't list tasks: {e}")
            return False
        return True
    
    def update_tasks(self, id: str) -> bool:
        try:
            task = list(self.cur.execute(f"SELECT * FROM Task_Manager WHERE task_id=?;", (id,)).fetchone())
            if len(task):
                print(task)
                title_input = input(f"Update task {id}, {task[1]} with Task Title (leave empty if no change): ")
                if title_input != "":
                    task[1] = title_input
                
                description_input = input(f"Update task {id}, {task[2]} with Task Description (leave empty if no change): ")
                if description_input != "":
                    task[2] = description_input
                    
                priority_input = input(f"Update task {id}, {task[4]} with Task Priority [LOW, MEDIUM, HIGH] (leave empty if no change): ")
                if priority_input != "":
                    if priority_input in ["LOW", "MEDIUM", "HIGH"]:
                        task[4] = priority_input
                    else:
                        raise Exception("Update failed because Priority input not in Priority Levels.")
                
                due_date_input = input(f"Update task {id}, {task[5]} with Due Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 (leave empty if no change): ")
                if due_date_input != "":
                    due_date_obj = datetime.strptime(due_date_input, "%Y-%m-%d %H:%M")
                    if due_date_obj < datetime.today():
                        raise Exception("Arg Due Date is in the past, set a future date.")
                    task[5] = due_date_obj
                
                category_input = input(f"Update task {id}, {task[6]} with Category (leave empty if no change): ")
                if category_input != "":
                    task[6] = category_input
                    
                update_query = """UPDATE Task_Manager SET title=?, description=?, priority=?, due_date=?, category=? WHERE task_id=?;"""
                self.cur.execute(update_query, (task[1], task[2], task[4], task[5], task[6], task[0]))
            else:
                raise Exception("ID not in Tasks, check the list of tasks.")
            
        except Exception as e:
            print(f"Couldn't update Task: {e}")
            return False
        return True
    
    
    def delete_tasks(self, id: str) -> bool:
        try:
            task = list(self.cur.execute(f"SELECT * FROM Task_Manager WHERE task_id=?;", (id,)).fetchone())
            print(task)
            if len(task):
                delete_query = f"DELETE FROM Task_Manager WHERE task_id={task[0]};"
                self.cur.execute(delete_query)
            else:
                raise Exception("ID not in Tasks, check the list of tasks.")
        except Exception as e:
            print(f"Couldn't delete Task: {e}")
            return False
        return True
    
    def search_tasks(self) -> bool:
        try:
            selected_tasks = dict()
            search_strategy = input("Search Strategy (due_date, priority, category, created_at): ")
            if search_strategy in ["due_date", "priority", "category", "created_at"]:
                if search_strategy in ["due_date", "created_at"]:
                    from_date_input = datetime.strptime(input(f"{search_strategy.capitalize()} - From Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 : "), "%Y-%m-%d %H:%M")
                    to_date_input = datetime.strptime(input(f"{search_strategy.capitalize()} - To Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 : "), "%Y-%m-%d %H:%M")
                    search_query = f"SELECT * FROM Task_Manager WHERE {search_strategy} >= '{from_date_input}' AND {search_strategy} <= '{to_date_input}';"
                            
                elif search_strategy == "priority":
                    priority_input = input(f"Task Priority [LOW, MEDIUM, HIGH] to search: ")
                    if priority_input not in ["LOW", "MEDIUM", "HIGH"]:
                        raise Exception("Priority Input not in Priority Levels.")
                    search_query = f"SELECT * FROM Task_Manager WHERE {search_strategy} = '{priority_input}';"
                            
                elif search_strategy == "category":
                    category_input = input(f"Task Category to search: ")
                    search_query = f"SELECT * FROM Task_Manager WHERE {search_strategy} = '{category_input}';"
                            
                self.list_tasks(custom_query=search_query)
            else:
                raise Exception("Input Search Strategy not in Strategies list.")
            
        except Exception as e:
            print(f"Couldn't search: {e}")
            return False
        return True
    
    def sort_tasks(self) -> bool:
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
        try:
            task = list(self.cur.execute(f"SELECT * FROM Task_Manager WHERE task_id=?;", (id,)).fetchone())
            if len(task):
                current_status = task[3]
                new_status = not current_status
                update_query = """UPDATE Task_Manager SET is_completed=? WHERE task_id=?;"""
                self.cur.execute(update_query, (new_status, task[0]))
                print(f"Task {id} completion status toggled to: {new_status}")
            else:
                raise Exception("ID not in Tasks, check the list of tasks.")
        except Exception as e:
            print(f"Couldn't toggle completion status: {e}")
            return False
        return True
            
    
    
    ### JSON Version
    
    # def open_json(self, path: Path) -> bool:
    #     self.path = path
    #     try:
    #         with open(self.path, "r") as read:
    #             self.tasks = json.load(read)
    #     except Exception as e:
    #         print(f"Couldn't open the JSON: {e}")
    #         return False
    #     return True
    
    # def dump_json(self) -> bool:
    #     try:
    #         with open(self.path, "w") as write:
    #             json.dump(self.tasks, write, indent=4)
    #     except Exception as e:
    #         print(f"Couldn't dump the JSON: {e}")
    #         return False
    #     return True
    
    # def create_task(self, task: str, priority: str, due_date: str, category: str) -> bool:
    #     try:
    #         if self.tasks != None:
    #             description = input(f"Description for the task {task}: ")
    #             created_at = datetime.now().isoformat()
    #             due_date_obj = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
    #             dict_task = {
    #                 "title": task,
    #                 "description": description,
    #                 "created_at": created_at,
    #                 "priority": priority,
    #                 "due_date": due_date_obj.isoformat(),
    #                 "category": category
    #             }
    #             if check_json_empty(self.tasks):
    #                 new_task =  {1 : dict_task}
    #                 self.tasks.update(new_task)
    #             else:
    #                 tasks_keys = self.tasks.keys()
    #                 max_keys = max(tasks_keys)
                    
    #                 new_task = {int(max_keys) + 1: dict_task}
    #                 self.tasks.update(new_task)
    #     except Exception as e:
    #         print(f"Couldn't create task: {e}")
    #         return False
    #     return True


    # def list_tasks(self, selected_tasks=None) -> bool:
    #     try:
    #         if not selected_tasks:
    #             for id, task in self.tasks.items():
    #                 print(f"Id: {id}\tTask: {pprint.pformat(task)}")
    #         else:
    #             for id, task in selected_tasks.items():
    #                 print(f"Id: {id}\tTask: {pprint.pformat(task)}")
    #     except Exception as e:
    #         print(f"Couldn't list tasks: {e}")
    #         return False
    #     return True

    # def update_tasks(self, id: str) -> bool:
    #     try:    
    #         if check_id_exists_in_tasks(id, self.tasks):
    #             title_input = input(f"Update task {id}, {self.tasks[id]['title']} with Task Title (leave empty if no change): ")
    #             if title_input != "":
    #                 self.tasks[id]['title'] = title_input
                
    #             description_input = input(f"Update task {id}, {self.tasks[id]['description']} with Task Description (leave empty if no change): ")
    #             if description_input != "":
    #                 self.tasks[id]['description'] = description_input
                    
    #             priority_input = input(f"Update task {id}, {self.tasks[id]['priority']} with Task Priority [LOW, MEDIUM, HIGH] (leave empty if no change): ")
    #             if priority_input != "":
    #                 if priority_input in ["LOW", "MEDIUM", "HIGH"]:
    #                     self.tasks[id]['priority'] = priority_input
    #                 else:
    #                     raise Exception("Update failed because Priority input not in Priority Levels.")
                
    #             due_date_input = input(f"Update task {id}, {self.tasks[id]['due_date']} with Due Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 (leave empty if no change): ")
    #             if due_date_input != "":
    #                 due_date_obj = datetime.strptime(due_date_input, "%Y-%m-%d %H:%M")
    #                 if due_date_obj < datetime.today():
    #                     raise Exception("Arg Due Date is in the past, set a future date.")
    #                 self.tasks[id]['due_date'] = due_date_obj.isoformat()
                
    #             category_input = input(f"Update task {id}, {self.tasks[id]['category']} with Category (leave empty if no change): ")
    #             if category_input != "":
    #                 self.tasks[id]['category'] = category_input
                    
    #             # self.tasks[id]['created_at'] = datetime.now().isoformat()
    #         else:
    #             raise Exception("ID not in Tasks, check the list of tasks.")
    #     except Exception as e:
    #         print(f"Couldn't update Task: {e}")
    #         return False
    #     return True

    # def delete_tasks(self, id: str) -> bool:
    #     try:
    #         if check_id_exists_in_tasks(id, self.tasks):
    #             self.tasks.pop(id)
    #         else:
    #             raise Exception("ID not in Tasks, check the list of tasks.")
    #     except Exception as e:
    #         print(f"Couldn't delete Task: {e}")
    #         return False
    #     return True
    
    # def search_tasks(self) -> bool:
    #     try:
    #         selected_tasks = dict()
    #         search_strategy = input("Search Strategy (due_date, priority, category, created_at): ")
    #         if search_strategy in ["due_date", "priority", "category", "created_at"]:
    #             if search_strategy in ["due_date", "created_at"]:
    #                 from_date_input = datetime.strptime(input(f"{search_strategy.capitalize()} - From Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 : "), "%Y-%m-%d %H:%M")
    #                 to_date_input = datetime.strptime(input(f"{search_strategy.capitalize()} - To Date with format: Year-Month-Day Hour:Minutes. Eg: 2026-01-01 13:11 : "), "%Y-%m-%d %H:%M")
                    
    #                 for id, task in self.tasks.items():
    #                     if datetime.fromisoformat(task[search_strategy]) >= from_date_input and datetime.fromisoformat(task[search_strategy]) <= to_date_input:
    #                         selected_tasks[id] = task
                            
    #             elif search_strategy == "priority":
    #                 priority_input = input(f"Task Priority [LOW, MEDIUM, HIGH] to search: ")
    #                 if priority_input not in ["LOW", "MEDIUM", "HIGH"]:
    #                     raise Exception("Priority Input not in Priority Levels.")
                    
    #                 for id, task in self.tasks.items():
    #                     if task[search_strategy] == priority_input:
    #                         selected_tasks[id] = task
                            
    #             elif search_strategy == "category":
    #                 category_input = input(f"Task Category to search: ")
                    
    #                 for id, task in self.tasks.items():
    #                     if task[search_strategy] == category_input:
    #                         selected_tasks[id] = task
                            
    #             self.list_tasks(selected_tasks=selected_tasks)
                        
    #         else:
    #             raise Exception("Input Search Strategy not in Strategies list.")
            
    #     except Exception as e:
    #         print(f"Couldn't search: {e}")
    #         return False
    #     return True
    
    # def sort_tasks(self) -> bool:
    #     try:
    #         selected_tasks = dict()
    #         sort_strategy = input("Search Strategy (due_date, priority, created_at): ")
    #         if sort_strategy in ["due_date", "priority", "created_at"]:
    #             if sort_strategy in ["due_date", "created_at"]:
    #                 selected_tasks = dict(sorted(self.tasks.items(), key= lambda item: item[1][sort_strategy]))
                            
    #             elif sort_strategy == "priority":
    #                 priority_levels = {
    #                     "HIGH": 3,
    #                     "MEDIUM": 2,
    #                     "LOW": 1
    #                 }
    #                 selected_tasks = dict(sorted(self.tasks.items(), key= lambda item: (-priority_levels.get(item[1][sort_strategy], 0), item[1]["due_date"])))
                            
    #             self.list_tasks(selected_tasks=selected_tasks)
                        
    #         else:
    #             raise Exception("Input Search Strategy not in Strategies list.")
            
    #     except Exception as e:
    #         print(f"Couldn't Sort: {e}")
    #         return False
    #     return True