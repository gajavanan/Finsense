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
Supply Neon (`DATABASE_URL`) and optional AI providers.
- Local dev: `DATABASE_URL=sqlite:///./finsense.db`
- Production Neon: `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require`

## Authentication Architecture

FinSense utilizes simple, secure authentication with email and password:

```
1. Registration:
User enters Full Name, Email, Mobile (+91), Password
  ↓ POST /api/v1/auth/register {name, email, phone_number, password}
FastAPI validates full name, email format, 10-digit Indian mobile, password
  ↓
User created directly in PostgreSQL with bcrypt hashed password

2. Sign In:
User signs in with Email + Password
  ↓ POST /api/v1/auth/login {email, password}
FastAPI verifies password (bcrypt)
  ↓
Issues standard FinSense JWT access token {sub=user.id, email, exp}
```

- **Account Identifier:** Email is the unique login identifier.
- **Mobile Number:** Collected during registration as profile data (+91 Indian mobile validation).
- **Password Hashing:** `bcrypt.hashpw` / `bcrypt.checkpw` (salted, high cost).
- **Session Tokens:** Stateless JWT access tokens signed with `JWT_SECRET_KEY` on FastAPI.
- **Password Reset:** Handled via secure email reset link (Resend / SMTP).

## Architecture
React (Vercel) → FastAPI (Render) → Neon PostgreSQL
