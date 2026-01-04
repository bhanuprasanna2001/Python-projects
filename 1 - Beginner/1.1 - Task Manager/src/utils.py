import os
import json
from pathlib import Path

def create_tasks_json_if_not_exists(path: Path):
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
    return len(json) == 0

def check_id_exists_in_tasks(id, tasks) -> bool:
    return id in tasks.keys()