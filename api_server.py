"""
DermAI — API Server v2
-----------------------
Now supports personality modes:
  friend, boyfriend, girlfriend, sister, mum, doctor
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from skin_engine import chat_with_dermai, detect_emotion, PERSONALITIES

app = FastAPI(title="DermAI API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory sessions
sessions: dict = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    personality: Optional[str] = "friend"   # friend | boyfriend | girlfriend | sister | mum | doctor

class EmotionRequest(BaseModel):
    text: str


@app.get("/")
def root():
    return {
        "service": "DermAI API v2",
        "personalities": list(PERSONALITIES.keys()),
        "endpoints": {
            "POST /chat":              "Main conversation (supports personality param)",
            "POST /emotion":           "Detect emotion in text",
            "GET  /personalities":     "List all available personalities",
            "GET  /session/{id}":      "Get session history",
            "DELETE /session/{id}":    "Clear session",
            "GET  /health":            "Health check",
        }
    }


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Send a message and get an emotion-aware, personality-driven response.

    Example:
    {
      "session_id": "user_123",
      "message": "my skin is so oily i hate it",
      "personality": "sister"
    }
    """
    # Validate personality
    personality = req.personality if req.personality in PERSONALITIES else "friend"

    # Get or create session
    if req.session_id not in sessions:
        sessions[req.session_id] = {
            "history": [],
            "skin_profile": {},
            "personality": personality
        }

    session = sessions[req.session_id]

    # Use personality from skin profile if user set it mid-conversation
    active_personality = session["skin_profile"].get("personality", personality)

    result = chat_with_dermai(
        user_message=req.message,
        conversation_history=session["history"],
        skin_profile=session["skin_profile"],
        personality=active_personality
    )

    # Update session
    session["history"].append({"role": "user",      "content": req.message})
    session["history"].append({"role": "assistant", "content": result["reply"]})
    session["skin_profile"] = result["updated_profile"]

    # Keep last 20 messages
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    return {
        "reply":           result["reply"],
        "emotion":         result["emotion"],
        "skin_profile":    result["updated_profile"],
        "recommendations": result["recommendations"],
        "remedies":        result["remedies"],
        "stage":           result["stage"],
        "personality":     personality
    }


@app.get("/personalities")
def list_personalities():
    """List all available personalities with descriptions."""
    return {
        key: {
            "name": val["name"],
            "remedy_style": val["remedy_style"],
            "product_style": val["product_style"]
        }
        for key, val in PERSONALITIES.items()
    }


@app.post("/emotion")
def emotion_only(req: EmotionRequest):
    return detect_emotion(req.text)


@app.get("/session/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return sessions[session_id]


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"cleared": True}


@app.get("/health")
def health():
    import ollama
    try:
        models      = ollama.list()
        model_names = [m.model for m in models.models]
        llama_ready = any("llama3" in m for m in model_names)
        return {
            "status":           "ok",
            "ollama":           "connected",
            "llama3":           "ready" if llama_ready else "run: ollama pull llama3",
            "available_models": model_names
        }
    except Exception as e:
        return {
            "status": "degraded",
            "ollama": f"not reachable: {str(e)}",
            "fix":    "Run 'ollama serve' in a terminal"
        }
