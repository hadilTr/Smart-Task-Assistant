import json
import os
import requests
from datetime import datetime
from mcp.server.fastmcp import FastMCP

server = FastMCP(name="EmailNotificationServer")
CONFIG_FILE = "email_config.json"


def load_config():
    """Load email configuration from file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config):
    """Save email configuration to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


@server.tool(
    name="configure_testmail",
    description="Configure Testmail API settings. Required before sending emails."
)
def configure_testmail(
    api_key: str,
    namespace: str,
    default_from: str = None
):
    """
    Configure Testmail API settings.
    
    Args:
        api_key: Your Testmail API key
        namespace: Your Testmail namespace
        default_from: Default sender email address (optional, defaults to 'noreply@{namespace}.testmail.app')
    """
    if not default_from:
        default_from = f"noreply@{namespace}.testmail.app"
    
    config = {
        "api_key": api_key,
        "namespace": namespace,
        "default_from": default_from,
        "configured_at": datetime.now().isoformat()
    }
    
    # Test the API key
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Make a test request to validate credentials
        test_url = f"https://api.testmail.app/api/json?apikey={api_key}&namespace={namespace}&livequery=true"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            save_config(config)
            return {
                "message": "Testmail configuration successful! API key verified.",
                "config": {
                    "namespace": namespace,
                    "default_from": default_from,
                    "inbox_url": f"https://testmail.app/inbox/{namespace}"
                }
            }
        elif response.status_code == 401:
            return {
                "error": "Authentication failed. Invalid API key.",
                "hint": "Check your API key at https://testmail.app/account"
            }
        else:
            return {
                "error": f"API test failed with status code: {response.status_code}",
                "response": response.text
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Connection failed: {str(e)}",
            "hint": "Check your internet connection and try again."
        }


@server.tool(
    name="send_email",
    description="Send an email using Testmail. Supports HTML content and multiple recipients."
)
def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: str = None,
    html: bool = True
):
    """
    Send an email notification.
    
    Args:
        to: Recipient email address (e.g., 'user.66jry@inbox.testmail.app')
        subject: Email subject line
        body: Email body content (supports HTML if html=True)
        from_email: Sender email (optional, uses configured default)
        html: Send as HTML email (default: True)
    """
    config = load_config()
    
    if not config:
        return {
            "error": "Testmail not configured. Please use 'configure_testmail' tool first.",
            "hint": "Run configure_testmail with your API key and namespace."
        }
    
    try:
        url = "https://api.testmail.app/api/send"
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from": from_email or config['default_from'],
            "to": to,
            "subject": subject,
        }
        
        if html:
            payload["html"] = body
            # Also include text version
            plain_text = body.replace('<br>', '\n').replace('<br/>', '\n')
            # Simple HTML tag removal
            import re
            plain_text = re.sub('<[^<]+?>', '', plain_text)
            payload["text"] = plain_text
        else:
            payload["text"] = body
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "message": "Email sent successfully!",
                "details": {
                    "to": to,
                    "subject": subject,
                    "from": payload["from"],
                    "sent_at": datetime.now().isoformat(),
                    "message_id": result.get("message_id", "N/A")
                }
            }
        elif response.status_code == 401:
            return {
                "error": "Authentication failed. API key may have expired.",
                "hint": "Re-run configure_testmail with updated credentials."
            }
        else:
            return {
                "error": f"Failed to send email. Status code: {response.status_code}",
                "response": response.text
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to send email: {str(e)}",
            "hint": "Check your internet connection and recipient address."
        }


@server.tool(
    name="send_notification",
    description="Send a quick notification email with a pre-formatted template. Ideal for alerts, reminders, and status updates."
)
def send_notification(
    to: str,
    title: str,
    message: str,
    notification_type: str = "info",
    from_email: str = None
):
    """
    Send a formatted notification email.
    
    Args:
        to: Recipient email address (e.g., 'user.66jry@inbox.testmail.app')
        title: Notification title/subject
        message: Notification message content
        notification_type: Type of notification - 'info', 'success', 'warning', 'error' (default: 'info')
        from_email: Sender email (optional)
    """
    # Color scheme for notification types
    colors = {
        "info": "#3b82f6",      # blue
        "success": "#10b981",    # green
        "warning": "#f59e0b",    # amber
        "error": "#ef4444"       # red
    }
    
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    color = colors.get(notification_type.lower(), colors["info"])
    icon = icons.get(notification_type.lower(), icons["info"])
    
    # Create HTML body
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{icon} {title}</h2>
                </div>
                <div style="background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 5px 5px;">
                    <p style="margin: 0; white-space: pre-wrap;">{message}</p>
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                    <p style="font-size: 12px; color: #6b7280; margin: 0;">
                        Sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </div>
        </body>
    </html>
    """
    
    subject = f"[{notification_type.upper()}] {title}"
    
    return send_email(
        to=to,
        subject=subject,
        body=html_body,
        from_email=from_email,
        html=True
    )


@server.tool(
    name="get_inbox_emails",
    description="Retrieve emails from a Testmail inbox. Useful for checking sent emails and verifying delivery."
)
def get_inbox_emails(
    tag: str = None,
    limit: int = 10
):
    """
    Get emails from Testmail inbox.
    
    Args:
        tag: Inbox tag/user (optional, retrieves from all inboxes if not specified)
        limit: Maximum number of emails to retrieve (default: 10, max: 50)
    """
    config = load_config()
    
    if not config:
        return {
            "error": "Testmail not configured. Please use 'configure_testmail' tool first."
        }
    
    try:
        # Build URL
        url = f"https://api.testmail.app/api/json"
        params = {
            "apikey": config['api_key'],
            "namespace": config['namespace'],
            "limit": min(limit, 50)
        }
        
        if tag:
            params["tag"] = tag
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            emails = data.get("emails", [])
            
            # Format emails for readability
            formatted_emails = []
            for email in emails:
                formatted_emails.append({
                    "from": email.get("from"),
                    "to": email.get("to"),
                    "subject": email.get("subject"),
                    "timestamp": email.get("timestamp"),
                    "html": email.get("html", "")[:200] + "..." if len(email.get("html", "")) > 200 else email.get("html", ""),
                    "text": email.get("text", "")[:200] + "..." if len(email.get("text", "")) > 200 else email.get("text", "")
                })
            
            return {
                "count": len(formatted_emails),
                "emails": formatted_emails,
                "inbox_url": f"https://testmail.app/inbox/{config['namespace']}" + (f"/{tag}" if tag else "")
            }
        else:
            return {
                "error": f"Failed to retrieve emails. Status code: {response.status_code}",
                "response": response.text
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to retrieve emails: {str(e)}"
        }


@server.tool(
    name="get_email_config",
    description="View current Testmail configuration (API key is partially hidden for security)."
)
def get_email_config():
    """Get current email configuration."""
    config = load_config()
    
    if not config:
        return {
            "configured": False,
            "message": "Testmail is not configured. Use 'configure_testmail' tool to set up."
        }
    
    # Return config with masked API key
    safe_config = config.copy()
    api_key = safe_config['api_key']
    safe_config['api_key'] = api_key[:8] + "..." + api_key[-8:] if len(api_key) > 16 else "***HIDDEN***"
    
    return {
        "configured": True,
        "config": safe_config,
        "inbox_url": f"https://testmail.app/inbox/{config['namespace']}"
    }


@server.tool(
    name="generate_test_email",
    description="Generate a test email address for your namespace. Use this address to receive test emails."
)
def generate_test_email(tag: str):
    """
    Generate a test email address.
    
    Args:
        tag: Unique identifier for the inbox (e.g., 'user1', 'test', 'alerts')
    """
    config = load_config()
    
    if not config:
        return {
            "error": "Testmail not configured. Please use 'configure_testmail' tool first."
        }
    
    email_address = f"{tag}.{config['namespace']}@inbox.testmail.app"
    
    return {
        "email": email_address,
        "tag": tag,
        "namespace": config['namespace'],
        "inbox_url": f"https://testmail.app/inbox/{config['namespace']}/{tag}",
        "message": f"Use this email to receive test messages. View inbox at the URL above."
    }


if __name__ == "__main__":
    server.run()