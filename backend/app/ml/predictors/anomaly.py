import os, joblib, numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "anomaly_detector.joblib")

def load_anomaly():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)

def detect_anomaly(amount: float, historical_amounts: list, category: str = None):
    if len(historical_amounts) < 5:
        return {"is_anomaly": False, "score": 0, "reason": "Insufficient history for anomaly detection", "status":"insufficient_data"}
    amounts = np.array(historical_amounts).reshape(-1,1)
    model = load_anomaly()
    if model is None:
        # fallback: z-score
        mean = np.mean(historical_amounts)
        std = np.std(historical_amounts) or 1
        z = abs(amount - mean)/std
        is_anom = z > 2.5
        return {"is_anomaly": bool(is_anom), "score": round(float(-z),3), "reason": "Amount is significantly higher than normal spending pattern" if is_anom else "Normal transaction", "method":"zscore"}
    score = model.decision_function([[amount]])[0]
    pred = model.predict([[amount]])[0]  # -1 anomaly, 1 normal
    is_anom = pred == -1
    reason = "Amount is significantly higher than normal spending pattern" if is_anom else "Normal spending pattern"
    if amount > (np.mean(historical_amounts)+3*np.std(historical_amounts)):
        reason = "Amount is significantly higher than normal spending pattern"
    return {"is_anomaly": bool(is_anom), "score": round(float(score),3), "reason": reason, "method":"isolation_forest"}
