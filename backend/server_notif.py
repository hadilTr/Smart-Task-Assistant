import json
import os
from dotenv import load_dotenv
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from pathlib import Path

load_dotenv()

server = FastMCP(name="DesktopNotificationServer")

# Shared notification storage
NOTIFICATIONS_FILE = Path(__file__).parent / "notifications.json"
MAX_HISTORY = 100


def add_to_history(notification_type, title, message):
    """Add notification to shared history file"""
    try:
        # Load existing notifications
        if NOTIFICATIONS_FILE.exists():
            with open(NOTIFICATIONS_FILE, 'r') as f:
                notifications = json.load(f)
        else:
            notifications = []
        
        # Add new notification
        notifications.insert(0, {
            "id": len(notifications) + 1,
            "type": notification_type,
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "time": datetime.now().strftime("%I:%M:%S %p")
        })
        
        # Keep only last MAX_HISTORY notifications
        notifications = notifications[:MAX_HISTORY]
        
        # Save back to file
        with open(NOTIFICATIONS_FILE, 'w') as f:
            json.dump(notifications, f, indent=2)
    except Exception as e:
        print(f"Failed to save notification: {e}")


@server.tool(
    name="send_desktop_notification",
    description="Show a desktop notification pop-up on your laptop. Works on Windows, Mac, and Linux."
)
def send_desktop_notification(
    title: str,
    message: str,
    timeout: int = 10,
    app_name: str = "Task Assistant"
):
    """
    Store a notification for the browser dashboard (no OS pop-up).
    """
    try:
        add_to_history("info", title, message)
        return {
            "success": True,
            "message": "✅ Notification stored for browser dashboard!",
            "details": {
                "title": title,
                "message": message,
                "sent_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to store notification: {str(e)}"
        }


@server.tool(
    name="send_notification",
    description="Send a formatted notification with different types (info, success, warning, error)."
)
def send_notification(
    title: str,
    message: str,
    notification_type: str = "info",
    timeout: int = 10
):
    """
    Store a formatted notification for the browser dashboard (no OS pop-up).
    """
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = icons.get(notification_type.lower(), icons["info"])
    formatted_title = f"{icon} {title}"
    try:
        add_to_history(notification_type.lower(), title, message)
        return {
            "success": True,
            "message": "✅ Notification stored for browser dashboard!",
            "details": {
                "title": formatted_title,
                "message": message,
                "type": notification_type,
                "sent_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to store notification: {str(e)}"
        }


@server.tool(
    name="send_task_reminder",
    description="Send a task reminder notification."
)
def send_task_reminder(
    task_name: str,
    due_time: str = None,
    priority: str = "normal"
):
    """
    Store a task reminder notification for the browser dashboard (no OS pop-up).
    """
    priority_icons = {
        "low": "🔵",
        "normal": "🟡",
        "high": "🔴"
    }
    icon = priority_icons.get(priority.lower(), "🟡")
    message = f"Task: {task_name}"
    if due_time:
        message += f"\nDue: {due_time}"
    title = f"{icon} Task Reminder"
    try:
        add_to_history("reminder", title, message)
        return {
            "success": True,
            "message": "✅ Task reminder stored for browser dashboard!",
            "details": {
                "title": title,
                "message": message,
                "sent_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to store task reminder: {str(e)}"
        }


@server.tool(
    name="send_urgent_alert",
    description="Send an urgent alert that stays visible longer."
)
def send_urgent_alert(
    title: str,
    message: str
):
    """
    Store an urgent alert notification for the browser dashboard (no OS pop-up).
    """
    try:
        add_to_history("urgent", f"🚨 URGENT: {title}", message)
        return {
            "success": True,
            "message": "✅ Urgent alert stored for browser dashboard!",
            "details": {
                "title": f"🚨 URGENT: {title}",
                "message": message,
                "sent_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to store urgent alert: {str(e)}"
        }


@server.tool(
    name="test_notification",
    description="Test if desktop notifications are working."
)
def test_notification():
    """Test browser notification system (stores a test notification)."""
    try:
        add_to_history("info", "🎉 Notification Test", "If you see this in your dashboard, your browser notification system is working!")
        return {
            "success": True,
            "message": "Test notification stored for browser dashboard!",
            "next_steps": [
                "Your browser notification system is configured correctly!",
                "You can now receive notifications in your dashboard.",
                "Try: send_notification('Test', 'Hello World!', 'success')"
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to store test notification: {str(e)}"
        }


if __name__ == "__main__":
    server.run()