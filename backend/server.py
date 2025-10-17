import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from dateparser import parse as date_parse
from dateparser.search import search_dates

load_dotenv()

server = FastMCP(name="SmartTaskAssistantServer")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["task_manager"]
tasks_collection = db["tasks"]


def get_next_task_id():
    """Generate the next task ID based on existing tasks."""
    last_task = tasks_collection.find_one(sort=[("id", -1)])
    return (last_task["id"] + 1) if last_task else 1


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


@server.resource("mongodb://")
def mongo_collection():
    """
    Exposes the MongoDB tasks collection as a FastMCP resource.
    """
    return tasks_collection


@server.tool(name="add_task", description="Add a new task with optional due date")
def add_task(title: str, due_date: str = None):
    parsed_due_date = None
    if due_date:
        parsed_due_date = parse_due_date(due_date)
        if not parsed_due_date:
            return {
                "error": f"Could not understand the due date: '{due_date}'. Try formats like '2025-10-15', 'tomorrow', 'next Monday', etc.",
                "received_date": due_date
            }
        
    task = {
        "id": get_next_task_id(),
        "title": title,
        "due_date": parsed_due_date,
        "done": False,
        "created_at": datetime.now().isoformat(),
    }
    
    tasks_collection.insert_one(task)
    
    # Remove MongoDB's _id from response
    task.pop("_id", None)
    
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
    
    task = tasks_collection.find_one({"id": task_id})
    
    if task:
        deleted_task = {
            "id": task["id"],
            "title": task["title"],
            "due_date": task.get("due_date"),
            "done": task.get("done"),
            "created_at": task.get("created_at")
        }
        tasks_collection.delete_one({"id": task_id})
        return {
            "message": f"Task '{deleted_task['title']}' (ID: {task_id}) has been deleted.",
            "deleted_task": deleted_task
        }
    
    return {"error": f"Task with ID {task_id} not found."}


@server.tool(name="list_tasks", description="List all existing tasks.")
def list_tasks():
    tasks = list(tasks_collection.find({}, {"_id": 0}).sort("id", 1))
    return {
        "tasks": tasks,
        "total_count": len(tasks)
    }


@server.tool(name="complete_task", description="Mark a task as completed by its ID.")
def complete_task(task_id: int):
    result = tasks_collection.update_one(
        {"id": task_id},
        {
            "$set": {
                "done": True,
                "completed_at": datetime.now().isoformat()
            }
        }
    )
    
    if result.matched_count > 0:
        task = tasks_collection.find_one({"id": task_id}, {"_id": 0})
        return {
            "message": f"Task '{task['title']}' (ID: {task_id}) marked as done.",
            "task": task
        }
    
    return {"error": f"Task with ID {task_id} not found."}


@server.tool(name="summarize_tasks", description="Summarize pending and completed tasks.")
def summarize_tasks():
    all_tasks = list(tasks_collection.find({}, {"_id": 0}))
    done = [t for t in all_tasks if t.get("done")]
    pending = [t for t in all_tasks if not t.get("done")]
    
    # Count overdue tasks
    today = datetime.now().strftime("%Y-%m-%d")
    overdue = [t for t in pending if t.get("due_date") and t["due_date"] < today]
    
    summary = f"You have {len(pending)} pending and {len(done)} completed tasks."
    if overdue:
        summary += f" {len(overdue)} tasks are overdue."
    
    return {
        "summary": summary,
        "pending": pending,
        "completed": done,
        "overdue": overdue,
        "stats": {
            "total": len(all_tasks),
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
    # Parse date from natural language
    parsed_due_date = parse_due_date(date)
    if not parsed_due_date:
        return {
            "error": f"Could not understand the date: '{date}'. Use YYYY-MM-DD or natural language like 'tomorrow', 'next Monday'.",
            "received_date": date
        }
    
    tasks_for_date = list(tasks_collection.find(
        {"due_date": parsed_due_date},
        {"_id": 0}
    ))
    
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

    # Filter tasks within the date range using MongoDB query
    tasks_in_range = list(tasks_collection.find(
        {
            "due_date": {
                "$gte": start_date_str,
                "$lte": end_date_str
            }
        },
        {"_id": 0}
    ))

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