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

# create tables (for sqlite dev; in prod use alembic upgrade head)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"DB create_all failed {e}")

app = FastAPI(title="FinSense API", version="1.0.0", description="FinSense – AI-Powered Personal Finance Advisor (Neon)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
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
    return {"message":"FinSense API running","docs":"/docs"}
