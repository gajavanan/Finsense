import logging
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "models"

@router.get("/health")
async def health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        # Safe logging server-side; do not expose database URLs, hostnames, or credentials to client
        logger.error(f"[HEALTH] Database check failed: {e}")
        db_status = "disconnected"

    categorizer_path = _MODELS_DIR / "transaction_categorizer.joblib"
    ml_status = "loaded" if categorizer_path.exists() else "training_required"

    overall_status = "ok" if db_status == "connected" else "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "ml_models": ml_status,
        "version": "1.0.0"
    }

@router.get("/ml/models")
async def ml_models():
    def exists(name: str) -> bool:
        return (_MODELS_DIR / name).exists()

    return [
        {"name": "Transaction Categorizer", "status": "loaded" if exists("transaction_categorizer.joblib") or exists("model.pkl") else "training_required"},
        {"name": "Spending Forecaster", "status": "loaded" if exists("spending_forecaster.joblib") else "training_required"},
        {"name": "Anomaly Detector", "status": "loaded" if exists("anomaly_detector.joblib") else "training_required"},
        {"name": "Budget Optimizer", "status": "loaded"},
        {"name": "Goal Predictor", "status": "loaded"},
    ]
