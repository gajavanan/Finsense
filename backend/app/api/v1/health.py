from fastapi import APIRouter, Depends
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()

@router.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:120]}"
    ml_status = "loaded" if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "transaction_categorizer.joblib")) else "training_required"
    return {"status":"healthy", "database": db_status, "ml_models": ml_status, "version":"1.0.0"}

@router.get("/ml/models")
async def ml_models():
    import os
    base=os.path.join(os.path.dirname(__file__), "..","..","ml","models")
    def exists(n): return os.path.exists(os.path.join(base,n))
    return [
        {"name":"Transaction Categorizer","status":"loaded" if exists("transaction_categorizer.joblib") else "training_required"},
        {"name":"Spending Forecaster","status":"loaded" if exists("spending_forecaster.joblib") else "training_required"},
        {"name":"Anomaly Detector","status":"loaded" if exists("anomaly_detector.joblib") else "training_required"},
        {"name":"Budget Optimizer","status":"loaded"},
        {"name":"Goal Predictor","status":"loaded"},
    ]
