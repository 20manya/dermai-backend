r"""
DermAI — Main Backend Server
-----------------------------
Combines:
  - AI chat (skin engine)
  - Auth (signup, login, OTP)
  - Orders (cart, wishlist, orders, payments)
  - Products catalog

Run locally:
  cd C:\Users\USER\Documents\dermai
  $env:GROQ_API_KEY="gsk_..."
  $env:SECRET_KEY="any-random-string"
  python -m uvicorn backend_server:app --reload --port 8000 --host 0.0.0.0

Deploy to Railway:
  Push to GitHub → connect Railway → set env vars → deploy
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json

from database import get_db, init_db, Product, SkinProfile, User
from auth import router as auth_router, get_current_user, verify_token
from orders import router as orders_router
from skin_engine import chat_with_dermai, detect_emotion, PERSONALITIES

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="DermAI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(orders_router)

# ── Initialize database on startup ───────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    print("[DermAI] Backend ready!")

# ── In-memory chat sessions ───────────────────────────────────────────────────
sessions: dict = {}

# ── Request models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message:     str
    personality: Optional[str] = "friend"
    token:       Optional[str] = None   # Optional — works without login too

class EmotionRequest(BaseModel):
    text: str

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "DermAI Backend",
        "version": "1.0.0",
        "endpoints": {
            "POST /chat":                "AI skin consultation",
            "POST /auth/signup/email":   "Email signup",
            "POST /auth/login/email":    "Email login",
            "POST /auth/otp/send":       "Send OTP",
            "POST /auth/otp/verify":     "Verify OTP + login",
            "GET  /cart":                "Get cart",
            "POST /cart/add":            "Add to cart",
            "GET  /wishlist":            "Get wishlist",
            "POST /wishlist/{id}":       "Toggle wishlist",
            "POST /orders/place":        "Place order",
            "GET  /orders":              "Order history",
            "GET  /products":            "Product catalog",
            "GET  /health":              "Health check",
        }
    }


@app.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Main AI chat endpoint.
    Works without login (guest mode).
    If token provided, saves skin profile to database.
    """
    # Get session ID — use user ID if logged in, else use "guest"
    user = None
    session_id = "guest"

    if req.token:
        user_id = verify_token(req.token)
        if user_id:
            user       = db.query(User).filter(User.id == user_id).first()
            session_id = user_id

    # Get or create session
    if session_id not in sessions:
        # If logged in, load skin profile from DB
        skin_profile = {}
        if user:
            profile = db.query(SkinProfile).filter(SkinProfile.user_id == user.id).first()
            if profile and profile.skin_type:
                skin_profile = {
                    "skin_type":   profile.skin_type,
                    "concerns":    json.loads(profile.concerns or "[]"),
                    "personality": profile.personality or "friend"
                }
        sessions[session_id] = {"history": [], "skin_profile": skin_profile}

    session     = sessions[session_id]
    personality = session["skin_profile"].get("personality", req.personality or "friend")

    # Call AI engine
    result = chat_with_dermai(
        user_message=req.message,
        conversation_history=session["history"],
        skin_profile=session["skin_profile"],
        personality=personality
    )

    # Update session
    session["history"].append({"role": "user",      "content": req.message})
    session["history"].append({"role": "assistant", "content": result["reply"]})
    session["skin_profile"] = result["updated_profile"]

    # Keep last 20 messages
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    # Save skin profile to DB if logged in
    if user and result["updated_profile"].get("skin_type"):
        profile = db.query(SkinProfile).filter(SkinProfile.user_id == user.id).first()
        if profile:
            profile.skin_type   = result["updated_profile"].get("skin_type")
            profile.concerns    = json.dumps(result["updated_profile"].get("concerns", []))
            profile.personality = result["updated_profile"].get("personality", "friend")
            db.commit()

    return {
        "reply":           result["reply"],
        "emotion":         result["emotion"],
        "skin_profile":    result["updated_profile"],
        "recommendations": result["recommendations"],
        "remedies":        result["remedies"],
        "stage":           result["stage"]
    }


@app.post("/emotion")
def emotion(req: EmotionRequest):
    return detect_emotion(req.text)


@app.get("/products")
def get_products(
    category: Optional[str] = None,
    search:   Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get product catalog with optional filtering"""
    query = db.query(Product).filter(Product.in_stock == True)
    if category and category != "All":
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%") |
            Product.brand.ilike(f"%{search}%")
        )
    products = query.all()
    return {"products": [
        {
            "id":       p.id,
            "name":     p.name,
            "brand":    p.brand,
            "price":    p.price,
            "category": p.category,
            "emoji":    p.emoji,
            "targets":  json.loads(p.targets or "[]"),
        } for p in products
    ]}


@app.get("/profile")
def get_profile(token: str, db: Session = Depends(get_db)):
    """Get user's saved skin profile"""
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    profile = db.query(SkinProfile).filter(SkinProfile.user_id == user_id).first()
    if not profile:
        return {"skin_profile": {}}
    return {
        "skin_profile": {
            "skin_type":   profile.skin_type,
            "concerns":    json.loads(profile.concerns or "[]"),
            "personality": profile.personality
        }
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "DermAI Backend v1.0.0"}
