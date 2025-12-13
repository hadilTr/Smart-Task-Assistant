import os
from dotenv import load_dotenv
import requests
from datetime import datetime

print("=" * 60)
print("MAILTRAP EMAIL SERVER TEST")
print("=" * 60)
print()

# Load environment variables
load_dotenv()

mailtrap_token = os.environ.get("MAILTRAP_API_TOKEN")

# Test 1: Check configuration
print("TEST 1: Environment Variables")
print("-" * 60)
print(f"MAILTRAP_API_TOKEN found: {bool(mailtrap_token)}")
if mailtrap_token:
    print(f"Token (masked): {mailtrap_token[:8]}...{mailtrap_token[-8:]}")
print()

# Test 2: Send a test email
print("TEST 2: Sending Test Email via Mailtrap")
print("-" * 60)

if not mailtrap_token:
    print("❌ ERROR: MAILTRAP_API_TOKEN not found in .env file")
    print("\nPlease add to your .env file:")
    print("MAILTRAP_API_TOKEN=your_token_here")
    exit(1)

try:
    url = "https://send.api.mailtrap.io/api/send"
    
    headers = {
        "Authorization": f"Bearer {mailtrap_token}",
        "Content-Type": "application/json"
    }
    
    # Change this to YOUR email address to receive the test
    test_recipient = input("Enter your email address to receive test: ").strip()
    
    if not test_recipient:
        test_recipient = "[email protected]"  # Default for testing
    
    payload = {
        "from": {
            "email": "hello@example.com",
            "name": "Test Sender"
        },
        "to": [
            {
                "email": test_recipient
            }
        ],
        "subject": "🎉 Mailtrap Test - Configuration Successful!",
        "html": """
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0;">
                            <h1 style="margin: 0;">✅ Success!</h1>
                            <p style="margin: 10px 0 0 0; opacity: 0.9;">Your Mailtrap integration is working</p>
                        </div>
                        <div style="background: #f8f9fa; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
                            <h2 style="color: #333; margin-top: 0;">Configuration Test Passed! 🎊</h2>
                            <p style="color: #666; line-height: 1.6;">
                                Your email server is properly configured and ready to send emails.
                                You can now use your chatbot to send notifications!
                            </p>
                            <div style="background: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                                <strong style="color: #667eea;">Next Steps:</strong>
                                <ul style="color: #666; line-height: 1.8;">
                                    <li>Start your MCP email server</li>
                                    <li>Connect your chatbot to the server</li>
                                    <li>Send test notifications</li>
                                </ul>
                            </div>
                            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                            <p style="color: #999; font-size: 12px; margin: 0;">
                                Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            </p>
                        </div>
                    </div>
                </body>
            </html>
        """,
        "text": "✅ Success! Your Mailtrap integration is working. Configuration test passed! You can now use your chatbot to send notifications."
    }
    
    print(f"Sending test email to: {test_recipient}")
    print("Please wait...")
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    print()
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS! Test email sent successfully!")
        print()
        print("Details:")
        print(f"  → To: {test_recipient}")
        print(f"  → Subject: {payload['subject']}")
        print(f"  → Message IDs: {result.get('message_ids', ['N/A'])}")
        print(f"  → Status: Sent at {datetime.now().strftime('%H:%M:%S')}")
        print()
        print("🎉 Your Mailtrap configuration is WORKING!")
        print()
        print("Next Steps:")
        print("  1. Check your email inbox for the test message")
        print("  2. Start your MCP server: python email_server.py")
        print("  3. Your chatbot is ready to send emails!")
        
    elif response.status_code == 401:
        print("❌ ERROR: Authentication Failed")
        print()
        print("Your API token is invalid or expired.")
        print()
        print("How to fix:")
        print("  1. Go to https://mailtrap.io")
        print("  2. Navigate to: Sending Domains → Your Domain → Integration")
        print("  3. Copy your API token")
        print("  4. Update MAILTRAP_API_TOKEN in your .env file")
        
    elif response.status_code == 422:
        error_data = response.json()
        print("❌ ERROR: Validation Failed")
        print()
        print("Details:", error_data.get('errors', 'Unknown validation error'))
        print()
        print("Common issues:")
        print("  • Email address format is invalid")
        print("  • Sender email doesn't match verified domain")
        print("  • Missing required fields")
        print()
        print("For testing, Mailtrap's sandbox allows any from/to addresses.")
        
    else:
        print(f"❌ ERROR: Request failed with status {response.status_code}")
        print()
        print("Response:", response.text)
        
except requests.exceptions.Timeout:
    print("❌ ERROR: Request timed out")
    print()
    print("Possible causes:")
    print("  • Slow internet connection")
    print("  • Mailtrap API is temporarily unavailable")
    print("  • Firewall blocking the connection")
    
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Connection failed")
    print()
    print("Please check:")
    print("  • Your internet connection")
    print("  • Firewall settings")
    print("  • VPN configuration")
    
except Exception as e:
    print(f"❌ ERROR: Unexpected error occurred")
    print()
    print(f"Error details: {str(e)}")
    print()
    print("Please report this error if it persists.")

print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)