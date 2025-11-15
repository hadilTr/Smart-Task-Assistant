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
from dotenv import load_dotenv

app = FastAPI(title="TaskFlow AI API")

load_dotenv()
frontend_path = os.getenv("FRONTEND_PATH")


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


@app.get("/")
async def get_home():
    """Serve the HTML frontend"""
    if frontend_path:
        html_file = Path(frontend_path)
    else: 
        return {"error": "FRONTEND_PATH environment variable not set"}
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    return {"message": "Problem in frontend path"}


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