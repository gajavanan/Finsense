import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dash_router
from app.api.v1.transactions import router as tx_router
from app.api.v1.budgets import router as budget_router
from app.api.v1.goals import router as goals_router
from app.api.v1.investments import router as inv_router
from app.api.v1.subscriptions import router as sub_router
from app.api.v1.reports import router as rep_router
from app.api.v1.advisor import router as adv_router
from app.api.v1.notifications import router as notif_router
from app.api.v1.fire import router as fire_router
from app.api.v1.ml import router as ml_router
from app.api.v1.ws import router as ws_router

logger = logging.getLogger(__name__)

# Non-destructive table initialization (creates tables if missing, never drops)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[DB] create_all notice: {e}")

# --- Non-destructive column verification for SQLite / PostgreSQL compatibility ---
def _ensure_phase1_columns():
    try:
        from sqlalchemy import text, inspect
        insp = inspect(engine)
        tx_cols = [c["name"] for c in insp.get_columns("transactions")] if insp.has_table("transactions") else []
        budget_cols = [c["name"] for c in insp.get_columns("budgets")] if insp.has_table("budgets") else []

        def add_col(table, col, ddl):
            exists = (col in tx_cols) if table == "transactions" else (col in budget_cols)
            if not exists:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
                    print(f"[MIGRATION] Added {table}.{col}")
                except Exception as ex:
                    msg = str(ex).lower()
                    if "duplicate column" not in msg and "already exists" not in msg:
                        print(f"[MIGRATION] {table}.{col} add skipped: {ex}")

        if insp.has_table("users"):
            add_col("users", "phone_number", "phone_number VARCHAR(20)")
            add_col("users", "phone_verified", "phone_verified BOOLEAN DEFAULT FALSE")
            add_col("users", "phone_verified_at", "phone_verified_at TIMESTAMP WITH TIME ZONE")
            try:
                with engine.begin() as conn:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users(phone_number)"))
            except Exception:
                pass

        if insp.has_table("transactions"):
            add_col("transactions", "transaction_type", "transaction_type VARCHAR")
            add_col("transactions", "subcategory", "subcategory VARCHAR")
            add_col("transactions", "source", "source VARCHAR DEFAULT 'manual'")
            add_col("transactions", "confidence_score", "confidence_score NUMERIC")
            # In PostgreSQL BOOLEAN requires DEFAULT FALSE (not 0)
            add_col("transactions", "is_anomaly", "is_anomaly BOOLEAN DEFAULT FALSE")
            add_col("transactions", "updated_at", "updated_at TIMESTAMP")

            # Backfill transaction_type from type where null
            try:
                with engine.begin() as conn:
                    conn.execute(text("UPDATE transactions SET transaction_type=type WHERE transaction_type IS NULL AND type IS NOT NULL"))
            except Exception:
                pass

            # Safe index creation
            try:
                with engine.begin() as conn:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_user_id_date ON transactions(user_id, date)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_category ON transactions(category)"))
            except Exception:
                pass

        if insp.has_table("budgets"):
            add_col("budgets", "monthly_limit", "monthly_limit NUMERIC")
            add_col("budgets", "year", "year VARCHAR")
            add_col("budgets", "updated_at", "updated_at TIMESTAMP")
            try:
                with engine.begin() as conn:
                    conn.execute(text("UPDATE budgets SET monthly_limit=amount WHERE monthly_limit IS NULL AND amount IS NOT NULL"))
            except Exception:
                pass
    except Exception as e:
        print(f"[MIGRATION] column verification notice: {e}")

_ensure_phase1_columns()

app = FastAPI(
    title="FinSense API",
    version="1.0.0",
    description="FinSense – AI-Powered Personal Finance Advisor"
)

@app.on_event("startup")
async def _startup_diagnostics():
    # Production-safe startup logging without exposing secrets or credentials
    try:
        db_type = "SQLite" if settings.DATABASE_URL.startswith("sqlite") else "PostgreSQL (Neon)"
        firebase_ready = bool(
            (settings.FIREBASE_PROJECT_ID and settings.FIREBASE_CLIENT_EMAIL and settings.FIREBASE_PRIVATE_KEY)
            or (settings.FIREBASE_CREDENTIALS_PATH and os.path.isfile(settings.FIREBASE_CREDENTIALS_PATH))
        )

        print("==================================================")
        print(f"[STARTUP] FinSense API starting up...")
        print(f"[STARTUP] Environment: {settings.APP_ENV}")
        print(f"[STARTUP] Database Engine: {db_type}")
        print(f"[STARTUP] Frontend URL: {settings.FRONTEND_URL}")
        print(f"[STARTUP] CORS Allowed Origins: {settings.cors_origins_list}")
        print(f"[STARTUP] Phone Auth Provider: Firebase Phone Authentication")
        print(f"[STARTUP] Firebase Admin Configured: {firebase_ready}")
        if settings.APP_ENV == "production" and not firebase_ready:
            print("[STARTUP WARNING] Firebase Admin credentials missing in production!")
        print("==================================================")
    except Exception as e:
        print(f"[STARTUP] Diagnostic log notice: {e}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health routes (both at root /health and /api/v1/health for Render/monitoring)
app.include_router(health_router, tags=["health"])
app.include_router(health_router, prefix="/api/v1", tags=["health"])

# API v1 feature routes
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(dash_router, prefix="/api/v1", tags=["dashboard"])
app.include_router(tx_router, prefix="/api/v1", tags=["transactions"])
app.include_router(budget_router, prefix="/api/v1", tags=["budgets"])
app.include_router(goals_router, prefix="/api/v1", tags=["goals"])
app.include_router(inv_router, prefix="/api/v1", tags=["investments"])
app.include_router(sub_router, prefix="/api/v1", tags=["subscriptions"])
app.include_router(rep_router, prefix="/api/v1", tags=["reports"])
app.include_router(adv_router, prefix="/api/v1", tags=["advisor"])
app.include_router(notif_router, prefix="/api/v1", tags=["notifications"])
app.include_router(fire_router, prefix="/api/v1", tags=["fire"])
app.include_router(ml_router, prefix="/api/v1", tags=["ml"])
app.include_router(ws_router, prefix="/api/v1", tags=["ws"])

@app.get("/")
async def root():
    return {
        "name": "FinSense API",
        "status": "running",
        "docs": "/docs"
    }
