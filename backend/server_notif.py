import json
import os
from dotenv import load_dotenv
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from plyer import notification
import platform

load_dotenv()

server = FastMCP(name="DesktopNotificationServer")


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
    Send a desktop notification that appears on your laptop screen.
    
    Args:
        title: Notification title
        message: Notification message
        timeout: How long to show notification in seconds (default: 10)
        app_name: Application name to display (default: "Task Assistant")
    """
    try:
        notification.notify(
            title=title,
            message=message,
            app_name=app_name,
            timeout=timeout
        )
        
        return {
            "success": True,
            "message": "✅ Desktop notification sent!",
            "details": {
                "title": title,
                "message": message,
                "platform": platform.system(),
                "sent_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to send notification: {str(e)}",
            "hint": "Make sure you have notification permissions enabled on your system"
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
    Send a desktop notification with emoji icons.
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: 'info', 'success', 'warning', or 'error' (default: 'info')
        timeout: Duration in seconds (default: 10)
    """
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    icon = icons.get(notification_type.lower(), icons["info"])
    formatted_title = f"{icon} {title}"
    
    return send_desktop_notification(
        title=formatted_title,
        message=message,
        timeout=timeout
    )


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
    Send a task reminder notification.
    
    Args:
        task_name: Name of the task
        due_time: When the task is due (optional)
        priority: 'low', 'normal', or 'high' (default: 'normal')
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
    
    return send_desktop_notification(
        title=title,
        message=message,
        timeout=15
    )


@server.tool(
    name="send_urgent_alert",
    description="Send an urgent alert that stays visible longer."
)
def send_urgent_alert(
    title: str,
    message: str
):
    """
    Send an urgent alert notification that stays visible longer.
    
    Args:
        title: Alert title
        message: Alert message
    """
    return send_desktop_notification(
        title=f"🚨 URGENT: {title}",
        message=message,
        timeout=30  # Stays for 30 seconds
    )


@server.tool(
    name="test_notification",
    description="Test if desktop notifications are working."
)
def test_notification():
    """Test desktop notification system."""
    
    result = send_desktop_notification(
        title="🎉 Notification Test",
        message="If you see this, your notification system is working perfectly!",
        timeout=5
    )
    
    if result.get("success"):
        result["next_steps"] = [
            "Your notification system is configured correctly!",
            "You can now receive notifications on your laptop",
            "Try: send_notification('Test', 'Hello World!', 'success')"
        ]
    
    return result


if __name__ == "__main__":
    server.run()