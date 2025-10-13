import json
import os
from datetime import datetime
import mcp
from mcp.server.fastmcp import FastMCP
import dateparser
from datetime import datetime

server = FastMCP(name="SmartTaskAssistantServer")
TASKS_FILE = "tasks.json"


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)

def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)



@server.tool(name="add_task", description="Add a new task with a title and optional due date.")
def add_task(title: str, due_date: str = None):
    tasks = load_tasks()

    if due_date:
        # Convert natural language date to YYYY-MM-DD
        parsed_date = dateparser.parse(due_date)
        if parsed_date:
            due_date = parsed_date.strftime("%Y-%m-%d")
        else:
            return {"error": "Could not understand the due date."}
        
    task = {
        "id": len(tasks) + 1,
        "title": title,
        "due_date": due_date,
        "done": False,
        "created_at": datetime.now().isoformat(),
    }
    tasks.append(task)
    save_tasks(tasks)
    return {"message": f"Task added: {title}", "task": task}



@server.tool(name="list_tasks", description="List all existing tasks.")
def list_tasks():
    tasks = load_tasks()
    return {"tasks": tasks}



@server.tool(name="complete_task", description="Mark a task as completed by its ID.")
def complete_task(task_id: int):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            save_tasks(tasks)
            return {"message": f"Task {task_id} marked as done."}
    return {"error": "Task not found."}



@server.tool(name="summarize_tasks", description="Summarize pending and completed tasks.")
def summarize_tasks():
    tasks = load_tasks()
    done = [t for t in tasks if t["done"]]
    pending = [t for t in tasks if not t["done"]]
    summary = f"You have {len(pending)} pending and {len(done)} completed tasks."
    return {"summary": summary, "pending": pending, "completed": done}


@server.tool(
    "tasks_by_date",
    description="List tasks for a specific date (supports natural language like 'tomorrow')."
)
def tasks_by_date(date: str):
    tasks = load_tasks()
    
    # Parse date from natural language
    parsed_date = dateparser.parse(date)
    if not parsed_date:
        return {"error": "Could not understand the date. Use YYYY-MM-DD or words like 'tomorrow'."}
    
    target_date = parsed_date.strftime("%Y-%m-%d")
    
    tasks_for_date = [
        t for t in tasks if t["due_date"] == target_date
    ]
    
    return {"date": target_date, "tasks": tasks_for_date}



if __name__ == "__main__":
    server.run()
