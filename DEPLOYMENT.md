# FinSense Production Deployment Guide

This document outlines the step-by-step procedure to deploy the FinSense AI-Powered Personal Finance Advisor into a secure, scalable production environment.

---

## 1. Production Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Vercel (React + Vite SPA)               │
│                 https://finsense.vercel.app             │
└────────────────────────────┬────────────────────────────┘
                             │ HTTPS API Calls (Bearer JWT)
                             ▼
┌─────────────────────────────────────────────────────────┐
│                 Render (FastAPI Backend)                │
│             https://finsense-api.onrender.com           │
└────────────────────────────┬────────────────────────────┘
                             │ SSL PostgreSQL (Port 5432)
                             ▼
┌─────────────────────────────────────────────────────────┐
│                 Neon (Serverless PostgreSQL)            │
│            ep-xyz-pooler.region.neon.tech/neondb        │
└─────────────────────────────────────────────────────────┘
```

- **Frontend**: Hosted on Vercel as a single-page application (SPA) with automatic HTML5 history rewrites.
- **Backend**: Hosted on Render Web Service running Uvicorn + FastAPI, bound to dynamic `$PORT`.
- **Database**: Serverless PostgreSQL hosted on Neon with connection pooling and SSL enforcement (`sslmode=require`).

> [!IMPORTANT]
> - Vercel connects **only** to Render via HTTPS.
> - Render connects **only** to Neon via SSL PostgreSQL.
> - The browser/frontend **never** connects directly to Neon.

---

## 2. Neon PostgreSQL Database Setup

1. Log into [Neon Console](https://console.neon.tech/).
2. Click **Create Project**:
   - **Project name**: `finsense-db`
   - **Postgres version**: `16` (or latest recommended)
   - **Region**: Choose a region geographically close to your Render service region (e.g., `US East (Ohio)` or `Frankfurt`).
3. Under the **Dashboard** of your project:
   - Locate the **Connection Details** card.
   - Ensure the connection type is set to **Pooled connection** (recommended for serverless compute).
   - Copy the connection string. It will look like:
     ```
     postgresql://username:password@ep-cool-pool-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   - **Do not remove `sslmode=require`**. Neon requires encrypted TLS connections.

---

## 3. Render Backend Web Service Setup

1. Log into [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository (`gajavanan/Finsense`).
4. Configure the service settings:
   - **Name**: `finsense-api`
   - **Region**: Same region as your Neon database.
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Pre-Deploy Command** (under Advanced):
     ```bash
     alembic upgrade head
     ```
   - **Health Check Path**: `/health`

---

## 4. Vercel Frontend Setup

1. Log into [Vercel Dashboard](https://vercel.com/).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository (`gajavanan/Finsense`).
4. Configure the project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click "Edit" and select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`
5. Configure Environment Variables (see Section 5 below).
6. Click **Deploy**.

---

## 5. Environment Variables Checklist

### A. Render Backend Variables (Configured in Render Dashboard)

Configure these in Render under **Environment Variables**:

| Variable Name | Value Description | Example / Placeholder |
|---|---|---|
| `APP_ENV` | Must be set to `production` | `production` |
| `PYTHON_VERSION` | Stable Python runtime | `3.12` |
| `DATABASE_URL` | Neon pooled PostgreSQL connection string | `postgresql://user:pass@ep-xyz-pooler.region.neon.tech/neondb?sslmode=require` |
| `JWT_SECRET_KEY` | High-entropy secret key (min 32 chars) | `<GENERATE_RANDOM_SECRET_KEY>` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan in minutes | `1440` |
| `FRONTEND_URL` | Production Vercel domain | `https://finsense-lovat.vercel.app` |
| `ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `https://finsense-lovat.vercel.app` |
| `FIREBASE_PROJECT_ID` | Firebase Project ID | `<YOUR_FIREBASE_PROJECT_ID>` |
| `FIREBASE_CLIENT_EMAIL` | Firebase Service Account Client Email | `<SERVICE_ACCOUNT_EMAIL>` |
| `FIREBASE_PRIVATE_KEY` | Firebase Service Account Private Key (keep full key with `\n`) | `-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n` |
| `EMAIL_PROVIDER` | Email provider (for password resets) | `resend` |
| `RESEND_API_KEY` | Resend HTTPS API Key (for password reset emails) | `re_123456789...` |
| `EMAIL_FROM` | Verified sender or Resend sandbox sender | `FinSense <onboarding@resend.dev>` |
| `OPENAI_API_KEY` | Optional OpenAI key for AI Financial Advisor | `<YOUR_OPENAI_KEY>` |

> [!IMPORTANT]
> **Firebase Phone Authentication Setup:**
> FinSense uses **Firebase Phone Authentication** for secure mobile number verification during registration.
> 
> ### Firebase Console & Credentials Setup
> 1. Open the [Firebase Console](https://console.firebase.google.com).
> 2. Create or select your **FinSense** project.
> 3. Go to **Authentication -> Sign-in method** and enable the **Phone** provider.
> 4. Go to **Authentication -> Settings -> Authorized domains** and add your production Vercel domain (e.g. `finsense-lovat.vercel.app`) and `localhost`.
> 5. Go to **Project Settings -> General -> Your apps**, register a Web App, and copy the config keys for Vercel frontend.
> 6. Go to **Project Settings -> Service accounts** and click **Generate new private key** to download your service account JSON.
> 7. Configure `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, and `FIREBASE_PRIVATE_KEY` in Render Dashboard under **Environment Variables**. (Never commit the JSON file to source control).

> [!TIP]
> Generate a cryptographically secure `JWT_SECRET_KEY` in your terminal using:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

### B. Vercel Frontend Variables (Configured in Vercel Dashboard)

Configure in Vercel under **Project Settings -> Environment Variables**:

| Variable Name | Description | Example / Placeholder |
|---|---|---|
| `VITE_API_URL` | Public HTTPS URL of the Render backend | `https://finsense-api.onrender.com` |
| `VITE_FIREBASE_API_KEY` | Firebase Web API Key | `AIzaSy...` |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase Auth Domain | `finsense-app.firebaseapp.com` |
| `VITE_FIREBASE_PROJECT_ID` | Firebase Project ID | `finsense-app` |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase Storage Bucket | `finsense-app.appspot.com` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Firebase Cloud Messaging Sender ID | `1234567890` |
| `VITE_FIREBASE_APP_ID` | Firebase Web App ID | `1:1234567890:web:...` |

> [!WARNING]
> Never add `FIREBASE_PRIVATE_KEY`, `DATABASE_URL`, or `JWT_SECRET_KEY` to Vercel environment variables. Vite injects variables prefixed with `VITE_` into client-side JavaScript bundles visible to any visitor.

---

## 6. Database Migrations

FinSense uses Alembic to manage database schema migrations safely and idempotently.

### Migration Commands
- **Run all pending migrations to head**:
  ```bash
  alembic upgrade head
  ```
- **Check current database revision**:
  ```bash
  alembic current
  ```
- **View migration history**:
  ```bash
  alembic history
  ```

### Automated Migration in Production
On Render, set the **Pre-Deploy Command** to:
```bash
alembic upgrade head
```
This ensures database migrations execute automatically before new application processes receive traffic.

---

## 7. Exact Deployment Order (12 Steps)

Follow this sequence to ensure zero-downtime and clean dependency resolution:

1. **STEP 1 — Create Neon Database**:
   Create the PostgreSQL project on Neon.
2. **STEP 2 — Retrieve Neon Connection String**:
   Copy the pooled connection string with `sslmode=require`.
3. **STEP 3 — Deploy Backend to Render**:
   Create the Web Service on Render with root directory `backend`.
4. **STEP 4 — Configure Render Environment Variables**:
   Set `APP_ENV=production`, `DATABASE_URL`, `JWT_SECRET_KEY`, and temporary `FRONTEND_URL` (`https://localhost`).
5. **STEP 5 — Execute Database Migrations**:
   Run `alembic upgrade head` (via Render Pre-Deploy Command or Render Shell).
6. **STEP 6 — Verify Backend Health**:
   Test in browser:
   ```
   https://YOUR-RENDER-SERVICE.onrender.com/health
   ```
   Expected response:
   ```json
   {"status": "ok", "database": "connected", "ml_models": "loaded", "version": "1.0.0"}
   ```
7. **STEP 7 — Deploy Frontend to Vercel**:
   Create the Vercel project with root directory `frontend`.
8. **STEP 8 — Set Vercel Environment Variable**:
   Add `VITE_API_URL=https://YOUR-RENDER-SERVICE.onrender.com`.
9. **STEP 9 — Retrieve Final Vercel Production Domain**:
   Copy the assigned domain (e.g., `https://finsense-abc.vercel.app`).
10. **STEP 10 — Update Render URLs**:
    In Render Dashboard, update:
    - `FRONTEND_URL=https://finsense-abc.vercel.app`
    - `ALLOWED_ORIGINS=https://finsense-abc.vercel.app`
11. **STEP 11 — Restart / Redeploy Backend**:
    Click "Manual Deploy" -> "Deploy latest commit" in Render to load updated CORS origins.
12. **STEP 12 — Verify End-to-End System**:
    Visit your Vercel URL and run through the verification checklist below.

---

## 8. Post-Deployment Verification Checklist

Verify all application workflows in production:

- [ ] **API Health**: Hit `https://YOUR-RENDER-SERVICE.onrender.com/health` -> returns `status: ok` and `database: connected`.
- [ ] **SPA Route Refresh**: Refreshing `/dashboard`, `/transactions`, `/ml-models`, `/budgets` on Vercel loads properly (no 404).
- [ ] **User Registration**: Register a new user with a valid email.
- [ ] **Email Verification**: Verification email arrives with link pointing to `https://YOUR-VERCEL-DOMAIN/verify-email?token=...` (not localhost).
- [ ] **User Login**: Log in with verified credentials and receive JWT session.
- [ ] **Dashboard Loading**: Financial summary cards and charts render without errors.
- [ ] **Manual Transaction**: Create an expense and an income transaction.
- [ ] **Bank Statement / CSV Upload**: Upload statement CSV -> transactions parsed and inserted into Neon.
- [ ] **Duplicate Detection**: Upload duplicate CSV -> duplicates detected and skipped.
- [ ] **ML Categorization**: Transaction categorizer assigns correct categories.
- [ ] **Budget Alerts**: Spending alerts trigger when expense crosses threshold.
- [ ] **Logout**: Log out cleanly and verify session destruction.

---

## 9. Troubleshooting Guide

| Issue | Likely Cause | Solution |
|---|---|---|
| `CORS error: No 'Access-Control-Allow-Origin' header` | Frontend domain not in backend whitelist | Ensure `FRONTEND_URL` and `ALLOWED_ORIGINS` in Render match your Vercel URL exactly (including `https://`, no trailing slash). |
| `[CONFIG ERROR] Production configuration validation failed` | Missing or weak environment variables | Check Render logs. Set valid `DATABASE_URL` (PostgreSQL), `JWT_SECRET_KEY` (min 32 chars), and production `FRONTEND_URL`. |
| `SSL connection has been closed unexpectedly` | Neon serverless idle disconnect | The SQLAlchemy engine is already configured with `pool_recycle=300` and `pool_pre_ping=True`. Ensure your connection string uses the `-pooler` endpoint. |
| `Vercel 404 on page refresh` | Missing SPA rewrite | Ensure `frontend/vercel.json` exists with the rewrite rule to `/index.html`. |
| `Verification emails not arriving` | SMTP configuration issue | Ensure `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, and an app-specific password (not personal Gmail password) is set in Render. |
| `Build failed: Module not found` | Build executed from wrong root directory | On Render, set Root Directory to `backend`. On Vercel, set Root Directory to `frontend`. |
