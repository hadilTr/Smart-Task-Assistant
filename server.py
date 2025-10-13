import json
import os
from datetime import datetime
import mcp
from mcp.server.fastmcp import FastMCP
from dateparser import parse as date_parse
from dateparser.search import search_dates

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


def parse_due_date(date_string: str):
    """
    Enhanced date parsing with better natural language support.
    Returns date in YYYY-MM-DD format or None if parsing fails.
    """
    if not date_string:
        return None
    
    # Try parsing with dateparser with specific settings for better accuracy
    parsed_date = date_parse(
        date_string,
        settings={
            'PREFER_DATES_FROM': 'future',  # Prefer future dates
            'RELATIVE_BASE': datetime.now(),
            'TIMEZONE': 'UTC'
        }
    )
    
    if parsed_date:
        return parsed_date.strftime("%Y-%m-%d")
    
    # Fallback: Try search_dates which can extract dates from longer text
    dates = search_dates(date_string, settings={'PREFER_DATES_FROM': 'future'})
    if dates and len(dates) > 0:
        return dates[0][1].strftime("%Y-%m-%d")
    
    return None


@server.tool(name="add_task", description="Add a new task with a title and optional due date.")
def add_task(title: str, due_date: str = None):
    tasks = load_tasks()

    parsed_due_date = None
    if due_date:
        parsed_due_date = parse_due_date(due_date)
        if not parsed_due_date:
            return {
                "error": f"Could not understand the due date: '{due_date}'. Try formats like '2025-10-15', 'tomorrow', 'next Monday', etc.",
                "received_date": due_date
            }
        
    task = {
        "id": len(tasks) + 1,
        "title": title,
        "due_date": parsed_due_date,
        "done": False,
        "created_at": datetime.now().isoformat(),
    }
    tasks.append(task)
    save_tasks(tasks)
    
    return {
        "message": f"Task added: {title}",
        "task": task,
        "parsed_date": parsed_due_date if parsed_due_date else "No due date"
    }


@server.tool(name="delete_task", description="Delete a task by its ID")
def delete_task(task_id: int):
    try:
        task_id = int(task_id)
    except ValueError:
        return {"error": "Task ID must be an integer."}
    
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            deleted_task = t.copy()
            tasks.remove(t)
            save_tasks(tasks)
            return {
                "message": f"Task '{deleted_task['title']}' (ID: {task_id}) has been deleted.",
                "deleted_task": deleted_task
            }
    return {"error": f"Task with ID {task_id} not found."}


@server.tool(name="list_tasks", description="List all existing tasks.")
def list_tasks():
    tasks = load_tasks()
    return {
        "tasks": tasks,
        "total_count": len(tasks)
    }


@server.tool(name="complete_task", description="Mark a task as completed by its ID.")
def complete_task(task_id: int):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            t["completed_at"] = datetime.now().isoformat()
            save_tasks(tasks)
            return {
                "message": f"Task '{t['title']}' (ID: {task_id}) marked as done.",
                "task": t
            }
    return {"error": f"Task with ID {task_id} not found."}


@server.tool(name="summarize_tasks", description="Summarize pending and completed tasks.")
def summarize_tasks():
    tasks = load_tasks()
    done = [t for t in tasks if t["done"]]
    pending = [t for t in tasks if not t["done"]]
    
    # Count overdue tasks
    today = datetime.now().strftime("%Y-%m-%d")
    overdue = [t for t in pending if t["due_date"] and t["due_date"] < today]
    
    summary = f"You have {len(pending)} pending and {len(done)} completed tasks."
    if overdue:
        summary += f" {len(overdue)} tasks are overdue."
    
    return {
        "summary": summary,
        "pending": pending,
        "completed": done,
        "overdue": overdue,
        "stats": {
            "total": len(tasks),
            "pending": len(pending),
            "completed": len(done),
            "overdue": len(overdue)
        }
    }


@server.tool(
    "tasks_by_date",
    description="List tasks for a specific date (supports natural language like 'tomorrow', 'next Monday')."
)
def tasks_by_date(date: str):
    tasks = load_tasks()
    
    # Parse date from natural language
    parsed_due_date = parse_due_date(date)
    if not parsed_due_date:
        return {
            "error": f"Could not understand the date: '{date}'. Use YYYY-MM-DD or natural language like 'tomorrow', 'next Monday'.",
            "received_date": date
        }
    
    tasks_for_date = [
        t for t in tasks if t["due_date"] == parsed_due_date
    ]
    
    return {
        "date": parsed_due_date,
        "date_input": date,
        "tasks": tasks_for_date,
        "count": len(tasks_for_date)
    }


@server.tool(
    name="tasks_by_range",
    description="List tasks within a date range. Supports natural language like 'this week', 'next 7 days', or specific dates like '2025-10-20 to 2025-10-25'."
)
def tasks_by_range(start: str, end: str = None):
    """
    Get tasks within a date range.
    
    Args:
        start: Start date (natural language or YYYY-MM-DD)
        end: End date (optional, defaults to same as start for single day)
    """
    tasks = load_tasks()

    # Parse start date with enhanced settings
    parsed_start = date_parse(
        start,
        settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now()
        }
    )
    
    if not parsed_start:
        return {
            "error": f"Could not understand start date: '{start}'. Try '2025-10-20', 'today', 'tomorrow', etc.",
            "received_start": start
        }

    # Parse end date
    if end:
        parsed_end = date_parse(
            end,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': parsed_start  # Base end date relative to start
            }
        )
        if not parsed_end:
            return {
                "error": f"Could not understand end date: '{end}'. Try '2025-10-25', 'next week', etc.",
                "received_end": end
            }
    else:
        # If no end date, assume single day (same as start)
        parsed_end = parsed_start

    # Ensure start is before or equal to end
    if parsed_start > parsed_end:
        parsed_start, parsed_end = parsed_end, parsed_start

    start_date_str = parsed_start.strftime("%Y-%m-%d")
    end_date_str = parsed_end.strftime("%Y-%m-%d")

    # Filter tasks within the date range
    tasks_in_range = [
        t for t in tasks
        if t.get("due_date") and start_date_str <= t["due_date"] <= end_date_str
    ]

    return {
        "start_date": start_date_str,
        "end_date": end_date_str,
        "start_input": start,
        "end_input": end if end else "same as start",
        "tasks": tasks_in_range,
        "count": len(tasks_in_range),
        "date_range_days": (parsed_end - parsed_start).days + 1
    }


if __name__ == "__main__":
    server.run()