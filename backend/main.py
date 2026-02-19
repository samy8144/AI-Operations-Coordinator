"""
FastAPI main application — serves the chat API and health endpoints.
"""
import traceback
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Skylark Drones AI Coordinator",
    description="Agentic AI system for drone operations coordination",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.get("/")
def root():
    return {"message": "Skylark Drones AI Coordinator API", "version": "1.0.0"}


@app.get("/api/status")
def get_status():
    try:
        from sheets_sync import sheets
        pilots = sheets.read_pilots()
        drones = sheets.read_drones()
        missions = sheets.read_missions()
        gs_connected = sheets.client is not None
        return {
            "status": "healthy",
            "google_sheets_connected": gs_connected,
            "pilots_loaded": len(pilots),
            "drones_loaded": len(drones),
            "missions_loaded": len(missions)
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "degraded",
            "google_sheets_connected": False,
            "pilots_loaded": 0,
            "drones_loaded": 0,
            "missions_loaded": 0,
            "error": str(e)
        }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        from agent import get_agent
        ag = get_agent()
        session_id = request.session_id or str(uuid.uuid4())
        response = ag.chat(request.message, session_id=session_id)
        return ChatResponse(response=response, session_id=session_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/{session_id}")
def clear_session(session_id: str):
    try:
        from agent import get_agent
        get_agent().clear_session(session_id)
    except Exception:
        pass
    return {"message": f"Session {session_id} cleared"}


@app.get("/api/data/pilots")
def get_pilots():
    from sheets_sync import sheets
    return sheets.read_pilots()


@app.get("/api/data/drones")
def get_drones():
    from sheets_sync import sheets
    return sheets.read_drones()


@app.get("/api/data/missions")
def get_missions():
    from sheets_sync import sheets
    return sheets.read_missions()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
