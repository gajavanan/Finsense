from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import secrets
import logging
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.models import User, Profile, LoginEvent
from app.core.config import settings
from app.services.email_service import send_login_notification, send_password_reset_email, send_test_email
from app.services.firebase_service import verify_firebase_phone_token

logger = logging.getLogger(__name__)

router = APIRouter()

# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    email: EmailStr
    password: str
    firebase_id_token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotRequest(BaseModel):
    email: EmailStr

class ResetRequest(BaseModel):
    token: str
    new_password: str

class TestEmailRequest(BaseModel):
    email: EmailStr

def _ua_parse(ua: str):
    ua = ua or ""
    browser = "Unknown"
    if "Chrome" in ua: browser = "Chrome"
    elif "Firefox" in ua: browser = "Firefox"
    elif "Safari" in ua and "Chrome" not in ua: browser = "Safari"
    elif "Edge" in ua: browser = "Edge"
    os = "Unknown"
    if "Windows" in ua: os = "Windows"
    elif "Mac" in ua: os = "macOS"
    elif "Android" in ua: os = "Android"
    elif "iPhone" in ua or "iPad" in ua: os = "iOS"
    elif "Linux" in ua: os = "Linux"
    device = "Desktop"
    if "Mobile" in ua: device = "Mobile"
    elif "Tablet" in ua: device = "Tablet"
    return browser, os, device

# -----------------------------------------------------------------------------
# Registration with Firebase Phone Authentication
# -----------------------------------------------------------------------------

@router.post("/auth/register")
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user verified via Firebase Phone Authentication:
    1. Validate email format and password length.
    2. Verify the Firebase ID token using Firebase Admin SDK.
    3. Extract the verified phone number from the cryptographically verified token claims.
    4. Ensure email and verified phone number are not already registered.
    5. Create user in FinSense database with phone_verified=True.
    """
    email_norm = payload.email.strip().lower()
    user_name = (payload.full_name or payload.name or "").strip()

    if not user_name:
        raise HTTPException(400, "Full name is required")

    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    # 1. Verify Firebase ID token and extract phone number
    try:
        verified_phone = verify_firebase_phone_token(payload.firebase_id_token)
    except ValueError as ve:
        raise HTTPException(400, str(ve))
    except RuntimeError as re:
        logger.error(f"[REGISTER] Firebase service error: {re}")
        raise HTTPException(500, "Firebase authentication service is temporarily unavailable.")
    except Exception as e:
        logger.error(f"[REGISTER] Unexpected verification error: {type(e).__name__}")
        raise HTTPException(400, "Unable to verify phone number via Firebase.")

    # 2. Check for duplicate email
    if db.query(User).filter(User.email == email_norm).first():
        raise HTTPException(400, "Email already registered")

    # 3. Check for duplicate phone number
    if db.query(User).filter(User.phone_number == verified_phone).first():
        raise HTTPException(400, "This mobile number is already registered to another account")

    # 4. Hash password and persist user
    hashed = get_password_hash(payload.password)
    now_utc = datetime.now(timezone.utc)

    user = User(
        id=str(uuid.uuid4()),
        email=email_norm,
        phone_number=verified_phone,
        phone_verified=True,
        phone_verified_at=now_utc,
        hashed_password=hashed,
        full_name=user_name,
        is_verified=True,  # legacy alias
    )
    db.add(user)
    profile = Profile(id=user.id, full_name=user_name, email=user.email)
    db.add(profile)
    db.commit()

    return {
        "status": "ok",
        "message": "Account created successfully. You can now sign in.",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "phone_verified": True
        }
    }

# -----------------------------------------------------------------------------
# Authentication & Session Management
# -----------------------------------------------------------------------------

@router.post("/auth/login")
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()

    # 1. Credential Verification
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}
        )

    # 2. Phone Verification Check
    # Existing users with phone_verified=True log in normally.
    # If phone is not verified, prompt user cleanly without crashing.
    if not user.phone_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PHONE_NOT_VERIFIED",
                "message": "Your phone number is not verified. Please register with a verified mobile number."
            }
        )

    # 3. Verified User - Issue FinSense JWT Access Token
    token = create_access_token({"sub": user.id, "email": user.email})
    ua = request.headers.get("user-agent", "")
    browser, os_name, device = _ua_parse(ua)

    now_utc = datetime.now(timezone.utc)
    last = db.query(LoginEvent).filter(LoginEvent.user_id == user.id).order_by(LoginEvent.created_at.desc()).first()
    should_email = True
    if last and last.created_at:
        last_time = last.created_at.replace(tzinfo=timezone.utc) if last.created_at.tzinfo is None else last.created_at
        if (now_utc - last_time).total_seconds() < 120 and last.user_agent == ua:
            should_email = False

    evt = LoginEvent(
        user_id=user.id,
        email=user.email,
        user_agent=ua,
        ip=request.client.host if request.client else None,
        device=device,
        browser=browser,
        os=os_name
    )
    db.add(evt)
    db.commit()

    if should_email:
        try:
            await send_login_notification(
                user.email,
                user.full_name or user.email.split("@")[0],
                ua, browser, os_name, device
            )
        except Exception as e:
            logger.warning(f"Login notification email skipped: {e}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "phone_verified": user.phone_verified
        }
    }

@router.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "phone_verified": user.phone_verified,
        "is_verified": user.phone_verified
    }

@router.post("/auth/logout")
async def logout(user: User = Depends(get_current_user)):
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# Password Reset Flow (Email-based)
# -----------------------------------------------------------------------------

@router.post("/auth/forgot-password")
async def forgot(payload: ForgotRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    msg = "If an account exists for this email, a password reset link has been sent."
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        try:
            await send_password_reset_email(user.email, user.full_name or "User", token)
        except Exception as e:
            logger.error(f"Password reset email delivery failed: {e}")
    return {"status": "ok", "message": msg}

@router.post("/auth/reset-password")
async def reset(payload: ResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()
    now_utc = datetime.now(timezone.utc)
    if not user or not user.reset_token_expires:
        raise HTTPException(400, "Invalid or expired reset token")

    token_exp = user.reset_token_expires.replace(tzinfo=timezone.utc) if user.reset_token_expires.tzinfo is None else user.reset_token_expires
    if token_exp < now_utc:
        raise HTTPException(400, "Invalid or expired reset token")

    if len(payload.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"status": "ok", "message": "Password reset successful"}

@router.post("/auth/test-email")
async def test_email(payload: TestEmailRequest):
    if settings.APP_ENV == "production":
        raise HTTPException(403, "Test email disabled in production")
    try:
        await send_test_email(payload.email.strip().lower())
        return {"status": "ok", "message": f"Test email sent to {payload.email}"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
