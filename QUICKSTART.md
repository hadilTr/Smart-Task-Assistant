# Smart Task Assistant - Quick Start Guide

## 🚀 Quick Start (Easiest Way)

Run this single command to start everything:

```bash
cd "e:\MCP\Smart Task Assistant\backend"
python start.py
```

This will:
- ✅ Check all requirements are installed
- ✅ Verify .env configuration
- ✅ Start the API server on port 8000
- ✅ Automatically connect to both MCP servers

Then open: **http://localhost:8000**

---

## 📋 What You Can Do

### Task Management
- `"Add a task to finish report by Friday"`
- `"Show all my tasks"`
- `"Complete task 5"`
- `"What's due next week?"`

### Email Notifications
- `"Configure testmail with API key YOUR_KEY and namespace YOUR_NS"`
- `"Send email to test@example.com"`
- `"Send me a reminder about task 3"`

### Combined Features
- `"Add task and notify me by email"`
- `"Complete task 5 and email team@company.com"`
- `"Summarize tasks and email the summary"`

---

## 🔧 Manual Setup

If you prefer to run manually:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python api_server.py
```

---

## 📧 Email Setup (Optional)

To use email features:

1. Get free Testmail account: https://testmail.app
2. Get your API key and namespace
3. In chat, send: `"Configure testmail with API key YOUR_KEY and namespace YOUR_NS"`

---

## 🎯 Architecture

```
Your Browser (chatbot.html)
    ↓
api_server.py (port 8000)
    ↓
client1.py (AI Agent)
    ↓ ↓
    ↓ └→ server_notif.py (Email)
    └→ server.py (Tasks)
```

---

## 🆘 Troubleshooting

**Port 8000 already in use?**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**MongoDB connection error?**
- Check your `.env` file has valid `MONGO_URI`
- Verify MongoDB Atlas is accessible

**Email not working?**
- Configure Testmail first
- Check configuration: `"Show email configuration"`

---

For detailed documentation, see `multi_server_guide.md`
