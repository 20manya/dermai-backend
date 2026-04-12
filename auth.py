"""
DermAI — Auth
--------------
Handles:
  - Email + password signup/login
  - Phone + OTP (using fast2sms — free Indian SMS API)
  - JWT tokens for session management
"""

import os
import uuid
import random
import string
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import httpx
from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, User, SkinProfile

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY      = os.environ.get("SECRET_KEY", "dermai-secret-change-in-production")
ALGORITHM       = "HS256"
TOKEN_EXPIRE    = 30  # days

# Fast2SMS API key (free at fast2sms.com — 100 free SMS/day)
FAST2SMS_KEY    = os.environ.get("FAST2SMS_KEY", "")

# In-memory OTP store (use Redis in production)
otp_store: dict = {}

# ── Request models ────────────────────────────────────────────────────────────
class EmailSignupRequest(BaseModel):
    name:     str
    email:    str
    password: str

class EmailLoginRequest(BaseModel):
    email:    str
    password: str

class PhoneSendOTPRequest(BaseModel):
    phone:    str   # 10-digit Indian number

class PhoneVerifyOTPRequest(BaseModel):
    phone:    str
    otp:      str
    name:     Optional[str] = None   # Required for new users

class TokenResponse(BaseModel):
    token:    str
    user_id:  str
    name:     str
    is_new:   bool = False

# ── JWT helpers ───────────────────────────────────────────────────────────────
def create_token(user_id: str) -> str:
    expire  = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def get_current_user(token: str, db: Session = Depends(get_db)) -> User:
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ── Password helpers ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ── OTP helpers ───────────────────────────────────────────────────────────────
def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))

async def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP via Fast2SMS (free Indian SMS service)"""
    if not FAST2SMS_KEY:
        # Dev mode — print OTP to console
        print(f"[DermAI] DEV MODE OTP for {phone}: {otp}")
        return True
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://www.fast2sms.com/dev/bulkV2",
                headers={"authorization": FAST2SMS_KEY},
                json={
                    "route":    "otp",
                    "variables_values": otp,
                    "numbers":  phone,
                }
            )
            return res.json().get("return", False)
    except:
        print(f"[DermAI] SMS failed — DEV OTP for {phone}: {otp}")
        return True   # Don't block in dev

# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/signup/email", response_model=TokenResponse)
async def signup_email(req: EmailSignupRequest, db: Session = Depends(get_db)):
    """Sign up with email + password"""
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        id            = str(uuid.uuid4()),
        name          = req.name,
        email         = req.email,
        password_hash = hash_password(req.password)
    )
    db.add(user)

    # Create empty skin profile
    db.add(SkinProfile(id=str(uuid.uuid4()), user_id=user.id))
    db.commit()

    return TokenResponse(token=create_token(user.id), user_id=user.id, name=user.name, is_new=True)


@router.post("/login/email", response_model=TokenResponse)
async def login_email(req: EmailLoginRequest, db: Session = Depends(get_db)):
    """Login with email + password"""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    return TokenResponse(token=create_token(user.id), user_id=user.id, name=user.name)


@router.post("/otp/send")
async def send_otp(req: PhoneSendOTPRequest):
    """Send OTP to phone number"""
    phone = req.phone.strip().replace("+91", "").replace(" ", "")
    if len(phone) != 10:
        raise HTTPException(400, "Enter a valid 10-digit Indian phone number")

    otp = generate_otp()
    # Store OTP with 10-minute expiry
    otp_store[phone] = {
        "otp":     otp,
        "expires": datetime.utcnow() + timedelta(minutes=10)
    }

    success = await send_otp_sms(phone, otp)
    if not success:
        raise HTTPException(500, "Failed to send OTP. Try again.")

    return {"message": f"OTP sent to {phone}", "dev_note": "Check server console for OTP in dev mode"}


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(req: PhoneVerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify OTP and login/signup"""
    phone = req.phone.strip().replace("+91", "").replace(" ", "")

    stored = otp_store.get(phone)
    if not stored:
        raise HTTPException(400, "OTP not sent or expired. Request a new one.")
    if datetime.utcnow() > stored["expires"]:
        del otp_store[phone]
        raise HTTPException(400, "OTP expired. Request a new one.")
    if stored["otp"] != req.otp:
        raise HTTPException(400, "Wrong OTP. Try again.")

    # OTP verified — clear it
    del otp_store[phone]

    # Check if user exists
    user = db.query(User).filter(User.phone == phone).first()
    is_new = False

    if not user:
        # New user — create account
        is_new = True
        user   = User(
            id    = str(uuid.uuid4()),
            name  = req.name or f"User{phone[-4:]}",
            phone = phone
        )
        db.add(user)
        db.add(SkinProfile(id=str(uuid.uuid4()), user_id=user.id))
        db.commit()

    return TokenResponse(token=create_token(user.id), user_id=user.id, name=user.name, is_new=is_new)


@router.get("/me")
async def get_me(token: str, db: Session = Depends(get_db)):
    """Get current user info"""
    user = get_current_user(token, db)
    return {
        "id":    user.id,
        "name":  user.name,
        "email": user.email,
        "phone": user.phone
    }
