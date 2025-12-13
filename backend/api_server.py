from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uvicorn
from pathlib import Path
from client1 import TaskAssistantAgent
import os
import json
from datetime import datetime
from dotenv import load_dotenv

app = FastAPI(title="TaskFlow AI API")

load_dotenv()
frontend_path = os.getenv("FRONTEND_PATH")

# Notification storage file
NOTIFICATIONS_FILE = Path(__file__).parent / "notifications.json"


# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent (will be done on startup)
agent = None


class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    response: str
    timestamp: str


@app.on_event("startup")
async def startup_event():
    """Initialize the agent when server starts"""
    global agent
    print("🚀 Initializing TaskFlow AI Agent...")
    agent = TaskAssistantAgent()
    await agent.setup()
    print("✅ Agent ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when server shuts down"""
    global agent
    if agent:
        await agent.cleanup()
    print("👋 Agent shutdown complete")


@app.get("/", response_class=HTMLResponse)
async def get_home():
    """Serve the HTML frontend"""

    html_file = Path(r"E:\MCP\Smart Task Assistant\chatbot.html")

    if not html_file.exists():
        return HTMLResponse(
            content="<h1>Frontend file not found</h1>",
            status_code=404
        )

    return html_file.read_text(encoding="utf-8")


@app.post("/api/chat")
async def chat(request: MessageRequest):
    """REST endpoint for chat messages"""
    if not agent:
        return {"error": "Agent not initialized"}
    
    try:
        response = await agent.run(request.message)
        from datetime import datetime
        return MessageResponse(
            response=response,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        return {"error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    print("✅ WebSocket client connected")
    
    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            print(f"📨 Received: {data}")
            
            # Send typing indicator
            await websocket.send_json({
                "type": "typing",
                "status": "started"
            })
            
            try:
                # Process message through agent
                response = await agent.run(data)
                
                # Send response back
                await websocket.send_json({
                    "type": "message",
                    "response": response,
                    "timestamp": asyncio.get_event_loop().time()
                })
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": str(e)
                })
            
            finally:
                # Stop typing indicator
                await websocket.send_json({
                    "type": "typing",
                    "status": "stopped"
                })
                
    except WebSocketDisconnect:
        print("👋 WebSocket client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None
    }


# Notification API Endpoints
def load_notifications():
    """Load notifications from file"""
    if NOTIFICATIONS_FILE.exists():
        try:
            with open(NOTIFICATIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


@app.get("/api/notifications")
async def get_notifications():
    """Get all notifications"""
    notifications = load_notifications()
    return notifications


@app.delete("/api/notifications")
async def clear_notifications():
    """Clear all notifications"""
    if NOTIFICATIONS_FILE.exists():
        NOTIFICATIONS_FILE.write_text("[]")
    return {"success": True, "message": "Notifications cleared"}


@app.get("/api/notifications/status")
async def get_notification_status():
    """Get notification system status"""
    notifications = load_notifications()
    return {
        "status": "connected",
        "count": len(notifications),
        "last_updated": datetime.now().isoformat()
    }


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting TaskFlow AI Server")
    print("=" * 60)
    print("📍 Frontend: http://localhost:8000")
    print("📍 API Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )