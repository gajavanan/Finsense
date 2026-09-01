# FinSense – AI-Powered Personal Finance Advisor

Production-ready web app: React + FastAPI + Neon + scikit-learn + OpenAI/Groq.

## Quick Start

### Frontend
```
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Backend
```
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py -m app.ml.training.train_all   # optional: trains ML models
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000  # http://localhost:8000/docs
# health: http://localhost:8000/api/v1/health
```

### Env
See `frontend/.env.example` and `backend/.env.example`
Supply Neon (`DATABASE_URL`), AI provider, and Firebase credentials.
- Local dev: `DATABASE_URL=sqlite:///./finsense.db`
- Production Neon: `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require`

## Authentication Architecture

FinSense utilizes a secure, mobile-first verification architecture powered by **Firebase Phone Authentication**:

```
1. Registration & Phone Verification:
User enters Name, Email, Mobile (+91), Password
  ↓
Frontend triggers Firebase invisible reCAPTCHA & sends SMS verification code
  ↓
Firebase delivers SMS OTP
  ↓
User enters 6-digit code on registration page
  ↓
Frontend confirms code with Firebase & retrieves verified Firebase ID token
  ↓ POST /api/v1/auth/register {name, email, password, firebase_id_token}
FastAPI backend verifies ID token cryptographically via Firebase Admin SDK
  ↓
Backend extracts verified phone number from token claims
  ↓
FinSense creates user: phone_number=verified_phone, phone_verified=true, phone_verified_at=now(UTC)

2. Sign In:
User signs in with Email + Password
  ↓ POST /api/v1/auth/login {email, password}
FastAPI verifies password (bcrypt) & checks phone_verified=true
  ↓
Issues standard FinSense JWT access token {sub=user.id, email, exp}
```

- **Account Identifier:** Email remains the unique login identifier.
- **Mobile Verification:** Exclusively performed via Firebase Phone Authentication during registration.
- **Password Hashing:** `bcrypt.hashpw` / `bcrypt.checkpw` (salted, high cost).
- **Session Tokens:** Stateless JWT access tokens signed with `JWT_SECRET_KEY` on FastAPI.
- **Unverified Access Gate:** Returns HTTP 403 `{"code":"PHONE_NOT_VERIFIED"}` blocking unverified logins.
- **Password Reset:** Handled via secure email reset link (Resend / SMTP).

### Firebase Credentials

**Backend (Render):**
- `FIREBASE_PROJECT_ID`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_PRIVATE_KEY`

**Frontend (Vercel):**
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

*Note: Secrets must never be committed to source code or exposed in frontend environment variables.*

## Architecture
React (Vercel) → FastAPI (Render) → Neon PostgreSQL → Firebase Phone Auth (Registration SMS) / Resend (Password Reset)
