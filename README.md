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
Supply Neon (DATABASE_URL), AI provider, Resend keys.
- Local dev: `DATABASE_URL=sqlite:///./finsense.db`
- Production Neon: `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require`

## Authentication Architecture
```
React (Zustand authStore)
  ↓ POST /api/v1/auth/login {email, password}
FastAPI (verify_password with bcrypt, check is_verified)
  ↓ create JWT {sub=user.id, email, exp}
Neon PostgreSQL / SQLite (users table: id, email, hashed_password, is_verified)
  ↓ Authorization: Bearer <JWT>
FastAPI GET /api/v1/auth/me → returns current user
```
- Password hashing: `bcrypt.hashpw` / `bcrypt.checkpw` (salted, never plain compare)
- Email normalization: `email.strip().lower()` on register & login
- Verified check returns 403 `{"code":"EMAIL_NOT_VERIFIED"}` distinct from 401
- No Supabase auth. Previous `supabase_realtime` publication removed.

## Architecture
React → FastAPI (JWT) → Neon PostgreSQL → ML / Resend → React
