import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from dateparser import parse as date_parse
from dateparser.search import search_dates
from pymongo.server_api import ServerApi
import re
from datetime import datetime, timedelta  

load_dotenv()

server = FastMCP(name="SmartTaskAssistantServer")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI,server_api=ServerApi('1'))
db = client["TaskAssistant"]
tasks_collection = db["tasks"]

"""try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)"""
    

def get_next_task_id():
    """Generate the next task ID based on existing tasks."""
    try:
        # Only find documents that HAVE an 'id' field
        last_task = tasks_collection.find_one(
            filter={"id": {"$exists": True}},  # ← CRITICAL: Only get docs with 'id'
            sort=[("id", -1)],
            projection={"id": 1, "_id": 0}  # Only return the 'id' field
        )
        
        if last_task and "id" in last_task:  # ← Double-check 'id' exists
            return last_task["id"] + 1
        else:
            return 1  # No valid tasks found
            
    except Exception as e:
        print(f"⚠️ Error: {e}")
        # Fallback: count documents and add 1
        return tasks_collection.count_documents({}) + 1

"""
def parse_due_date(date_string: str):

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
"""

def parse_due_date(date_string: str):
    """
    Enhanced date parsing with intelligent week handling.
    
    Week interpretations:
    - "next week" → Monday of next week
    - "this week" → Monday of current week (or today if past Monday)
    - "end of week" → Friday of current week
    - "end of next week" → Friday of next week
    - "beginning of next week" → Monday of next week
    
    Also supports all standard dateparser formats.
    """
    if not date_string:
        return None
    
    # Normalize input
    date_string_lower = date_string.lower().strip()
    now = datetime.now()
    current_weekday = now.weekday()  # Monday=0, Tuesday=1, ..., Sunday=6
    
    # === WEEK-BASED PATTERNS ===
    
    # Pattern: "next week" or "beginning of next week"
    if re.search(r'\b(next week|beginning of next week|start of next week)\b', date_string_lower):
        days_until_next_monday = (7 - current_weekday) if current_weekday != 0 else 7
        target_date = now + timedelta(days=days_until_next_monday)
        return target_date.strftime("%Y-%m-%d")
    
    # Pattern: "end of next week"
    if re.search(r'\bend of next week\b', date_string_lower):
        days_until_next_monday = (7 - current_weekday) if current_weekday != 0 else 7
        next_monday = now + timedelta(days=days_until_next_monday)
        next_friday = next_monday + timedelta(days=4)  # Monday + 4 = Friday
        return next_friday.strftime("%Y-%m-%d")
    
    # Pattern: "this week" or "beginning of this week"
    if re.search(r'\b(this week|beginning of this week|start of this week)\b', date_string_lower):
        if current_weekday == 0:  # Already Monday
            target_date = now
        else:
            # Go back to this week's Monday
            target_date = now - timedelta(days=current_weekday)
        return target_date.strftime("%Y-%m-%d")
    
    # Pattern: "end of week" or "end of this week"
    if re.search(r'\bend of (this )?week\b', date_string_lower):
        if current_weekday <= 4:  # Monday to Friday
            days_until_friday = 4 - current_weekday
            target_date = now + timedelta(days=days_until_friday)
        else:  # Saturday or Sunday - go to next Friday
            days_until_next_monday = 7 - current_weekday
            next_monday = now + timedelta(days=days_until_next_monday)
            target_date = next_monday + timedelta(days=4)
        return target_date.strftime("%Y-%m-%d")
    
    # Pattern: "in X weeks" → X weeks from today
    weeks_match = re.search(r'\bin (\d+) weeks?\b', date_string_lower)
    if weeks_match:
        num_weeks = int(weeks_match.group(1))
        target_date = now + timedelta(weeks=num_weeks)
        return target_date.strftime("%Y-%m-%d")
    
    # === DAY-BASED PATTERNS ===
    
    # Map weekday names to numbers
    weekday_map = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tue': 1, 'tues': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6
    }
    
    # Pattern: "next <weekday>" - go to the next occurrence of that weekday
    for day_name, day_num in weekday_map.items():
        if re.search(rf'\bnext {day_name}\b', date_string_lower):
            days_ahead = (day_num - current_weekday) % 7
            if days_ahead == 0:  # If today is that day, go to next week's instance
                days_ahead = 7
            target_date = now + timedelta(days=days_ahead)
            return target_date.strftime("%Y-%m-%d")
    
    # Pattern: "this <weekday>" - go to this week's occurrence (or today if that day)
    for day_name, day_num in weekday_map.items():
        if re.search(rf'\bthis {day_name}\b', date_string_lower):
            if current_weekday == day_num:
                target_date = now
            elif current_weekday < day_num:
                days_ahead = day_num - current_weekday
                target_date = now + timedelta(days=days_ahead)
            else:  # Already passed that day this week
                days_ahead = (7 - current_weekday) + day_num
                target_date = now + timedelta(days=days_ahead)
            return target_date.strftime("%Y-%m-%d")
    
    # === STANDARD DATEPARSER ===
    
    # Let dateparser handle everything else
    parsed_date = date_parse(
        date_string,
        settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': now,
            'TIMEZONE': 'UTC',
        }
    )
    
    if parsed_date:
        return parsed_date.strftime("%Y-%m-%d")
    
    # Fallback: Try search_dates for embedded dates
    dates = search_dates(date_string, settings={'PREFER_DATES_FROM': 'future'})
    if dates and len(dates) > 0:
        return dates[0][1].strftime("%Y-%m-%d")
    
    return None





def get_weekday_name(date_str):
    """Helper to show what day of week a date is"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.strftime("%A")




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
    #task.pop("_id", None)
    
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
    # Use custom parse_due_date (no settings parameter!)
    start_date_str = parse_due_date(start)
    
    if not start_date_str:
        return {
            "error": f"Could not understand start date: '{start}'. Try '2025-10-20', 'today', 'tomorrow', etc.",
            "received_start": start
        }

    # Parse end date
    if end:
        end_date_str = parse_due_date(end)
        if not end_date_str:
            return {
                "error": f"Could not understand end date: '{end}'. Try '2025-10-25', 'next week', etc.",
                "received_end": end
            }
    else:
        # If no end date, assume single day (same as start)
        end_date_str = start_date_str

    # Convert strings to datetime objects for comparison
    parsed_start = datetime.strptime(start_date_str, "%Y-%m-%d")
    parsed_end = datetime.strptime(end_date_str, "%Y-%m-%d")

    # Ensure start is before or equal to end
    if parsed_start > parsed_end:
        parsed_start, parsed_end = parsed_end, parsed_start
        start_date_str, end_date_str = end_date_str, start_date_str

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

    server.run(transport="stdio")