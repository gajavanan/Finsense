import os
from pathlib import Path
import joblib
import numpy as np
from datetime import date, timedelta

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = str(_MODELS_DIR / "spending_forecaster.joblib")

def load_forecaster():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)

def forecast_spending(historical: list, period: str = "30d"):
    # historical: list of {date, amount}
    if len(historical) < 7:
        return {"status": "insufficient_data", "message": "More transaction history is required. Need at least 7 days of data."}
    # simple LinearRegression on day index vs cumulative or daily amount
    # Use model if exists else train on fly
    amounts = [float(h.get("amount",0)) for h in historical]
    X = np.arange(len(amounts)).reshape(-1,1)
    y = np.array(amounts)
    model = load_forecaster()
    if model is None:
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)
    days_map = {"7d":7, "30d":30, "90d":90}
    n = days_map.get(period, 30)
    future_X = np.arange(len(amounts), len(amounts)+n).reshape(-1,1)
    preds = model.predict(future_X)
    preds = [max(0, float(p)) for p in preds]
    total_forecast = sum(preds)
    return {
        "status": "success",
        "period": period,
        "forecast": preds,
        "total_forecast": round(total_forecast,2),
        "historical": amounts,
        "model_loaded": os.path.exists(MODEL_PATH)
    }
