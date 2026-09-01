from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import secrets
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.models import User, Profile, LoginEvent
from app.core.config import settings
from app.services.email_service import send_login_notification, send_verification_email, send_password_reset_email, send_test_email

router = APIRouter()

# simple in-memory rate limiter for resend
_resend_cooldown: dict[str, datetime] = {}
RESEND_COOLDOWN_SECONDS = 60

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotRequest(BaseModel):
    email: EmailStr

class ResetRequest(BaseModel):
    token: str
    new_password: str

class ResendRequest(BaseModel):
    email: EmailStr

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

def _generate_verification_token() -> tuple[str, datetime]:
    # cryptographically secure, 24h expiry
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=24)
    return token, expires

@router.post("/auth/register")
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email_norm = payload.email.strip().lower()
    if db.query(User).filter(User.email == email_norm).first():
        raise HTTPException(400, "Email already registered")
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    # safe log without password
    print(f"[REGISTER] email={email_norm} name={payload.name}")
    hashed = get_password_hash(payload.password)
    token, expires = _generate_verification_token()
    user = User(
        id=str(uuid.uuid4()),
        email=email_norm,
        hashed_password=hashed,
        full_name=payload.name,
        is_verified=False,
        verification_token=token,
        verification_token_expires=expires,
    )
    db.add(user)
    profile = Profile(id=user.id, full_name=payload.name, email=user.email)
    db.add(profile)
    db.commit()
    print(f"[EMAIL VERIFICATION] Recipient: {email_norm} | SMTP configured: {bool(settings.SMTP_HOST and settings.SMTP_USER)} | Token expires: {expires.isoformat()} | Attempting real email send")
    try:
        await send_verification_email(user.email, payload.name, token)
        print(f"[REGISTER] Verification email sent successfully to {email_norm}")
    except Exception as e:
        # safe error without exposing password/token
        msg = str(e)
        if settings.SMTP_PASSWORD and settings.SMTP_PASSWORD in msg:
            msg = msg.replace(settings.SMTP_PASSWORD, "***")
        print(f"[REGISTER] Verification email failed for {email_norm}: {msg}")
        # Do not fail registration, but inform caller email may need resend
        # In production, you might want to return 500 if SMTP critical
        # Here we return 201 with message to check email / use resend
        return {"status": "ok", "message": "Registration successful. Verification email could not be sent - please use Resend verification. Error: " + msg[:120], "email_sent": False}
    return {"status": "ok", "message": "Registration successful. Check email for verification.", "email_sent": True}

@router.get("/auth/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    # Find user by token
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        print(f"[VERIFY] Invalid token attempt")
        raise HTTPException(400, "Invalid verification token")
    # Check already verified and token already used
    if user.is_verified and not user.verification_token:
        raise HTTPException(400, "Email already verified")
    # Check expiration
    if not user.verification_token_expires or user.verification_token_expires < datetime.utcnow():
        print(f"[VERIFY] Expired token for email={user.email}")
        raise HTTPException(400, "Verification token expired. Please request a new one.")
    # Check token reuse - if token doesn't match (already cleared)
    # Already ensured above
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    print(f"[VERIFY] Email verified successfully for {user.email}")
    return {"status": "verified", "message": "Email verified successfully"}

@router.post("/auth/resend-verification")
async def resend_verification(payload: ResendRequest, db: Session = Depends(get_db)):
    # Safe backend logging requested by task - do not log passwords/tokens
    print("Resend verification request received")
    print(f"[RESEND] Request received for endpoint /api/v1/auth/resend-verification method POST")
    try:
        email_norm = payload.email.strip().lower()
    except Exception:
        print("[RESEND] Invalid payload - missing email")
        raise HTTPException(422, "Email is required")
    print(f"[RESEND] Email field present: {bool(email_norm)} | Normalized email: {email_norm}")
    # Generic response to avoid email enumeration
    generic_ok = {"status": "ok", "message": "If an account exists for this email, a verification email has been sent."}
    user = db.query(User).filter(User.email == email_norm).first()
    if not user:
        print(f"[RESEND] Request for unknown email {email_norm}")
        return generic_ok
    if user.is_verified:
        raise HTTPException(400, "Email already verified")
    # Rate limiting
    last = _resend_cooldown.get(email_norm)
    if last and (datetime.utcnow() - last).total_seconds() < RESEND_COOLDOWN_SECONDS:
        remaining = int(RESEND_COOLDOWN_SECONDS - (datetime.utcnow() - last).total_seconds())
        raise HTTPException(429, f"Please wait {remaining}s before requesting another verification email.")
    _resend_cooldown[email_norm] = datetime.utcnow()
    # Generate new token, invalidate previous
    token, expires = _generate_verification_token()
    user.verification_token = token
    user.verification_token_expires = expires
    db.commit()
    print(f"[RESEND] New token for {email_norm} expires {expires.isoformat()}")
    try:
        await send_verification_email(user.email, user.full_name or user.email.split("@")[0], token)
        print(f"[RESEND] Verification email resent to {email_norm}")
    except Exception as e:
        msg = str(e)
        if settings.SMTP_PASSWORD and settings.SMTP_PASSWORD in msg:
            msg = msg.replace(settings.SMTP_PASSWORD, "***")
        print(f"[RESEND] Failed to send to {email_norm}: {msg}")
        raise HTTPException(500, f"Failed to send verification email: {msg[:150]}")
    return generic_ok

@router.post("/auth/test-email")
async def test_email(payload: TestEmailRequest):
    # Dev only - should be protected in production
    if settings.ENV == "production":
        raise HTTPException(403, "Test email disabled in production")
    try:
        await send_test_email(payload.email.strip().lower())
        print(f"[TEST EMAIL] Sent successfully to {payload.email}")
        return {"status": "ok", "message": f"Test email sent to {payload.email}"}
    except Exception as e:
        msg = str(e)
        if settings.SMTP_PASSWORD and settings.SMTP_PASSWORD in msg:
            msg = msg.replace(settings.SMTP_PASSWORD, "***")
        print(f"[TEST EMAIL] Failed: {msg}")
        raise HTTPException(500, detail=msg)

@router.post("/auth/login")
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    print(f"[LOGIN] attempt email={payload.email.strip().lower()} found={bool(user)} verified={getattr(user, 'is_verified', None) if user else None}")
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        print(f"[LOGIN] unverified email={user.email}")
        raise HTTPException(status_code=403, detail={"code": "EMAIL_NOT_VERIFIED", "message": "Please verify your email before signing in."})
    token = create_access_token({"sub": user.id, "email": user.email})
    ua = request.headers.get("user-agent","")
    browser, os_name, device = _ua_parse(ua)
    last = db.query(LoginEvent).filter(LoginEvent.user_id==user.id).order_by(LoginEvent.created_at.desc()).first()
    should_email = True
    if last and last.created_at and (datetime.utcnow() - last.created_at).total_seconds() < 120 and last.user_agent==ua:
        should_email = False
    evt = LoginEvent(user_id=user.id, email=user.email, user_agent=ua, ip=request.client.host if request.client else None, device=device, browser=browser, os=os_name)
    db.add(evt)
    db.commit()
    if should_email:
        try:
            await send_login_notification(user.email, user.full_name or user.email.split("@")[0], ua, browser, os_name, device)
        except Exception as e:
            print(f"login email failed {e}")
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "full_name": user.full_name}}

@router.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "is_verified": user.is_verified}

@router.post("/auth/logout")
async def logout(user: User = Depends(get_current_user)):
    return {"status": "ok"}

@router.post("/auth/forgot-password")
async def forgot(payload: ForgotRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    msg = "If an account exists for this email, a password reset link has been sent."
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        try:
            await send_password_reset_email(user.email, user.full_name or "User", token)
        except Exception as e:
            print(f"reset email failed {e}")
    return {"status": "ok", "message": msg}

@router.post("/auth/reset-password")
async def reset(payload: ResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired reset token")
    if len(payload.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"status": "ok", "message": "Password reset successful"}

@router.post("/login-notify")
async def login_notify_legacy(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent","")
    browser, os_name, device = _ua_parse(ua)
    try:
        await send_login_notification(user.email, user.full_name or user.email.split("@")[0], ua, browser, os_name, device)
    except: pass
    return {"status":"ok"}
