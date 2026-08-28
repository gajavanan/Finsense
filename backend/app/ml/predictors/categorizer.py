import os, joblib
from app.ml.preprocessing.text_features import combine_features

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "transaction_categorizer.joblib")

_model = None
_vectorizer = None

def load_model():
    global _model, _vectorizer
    if _model is not None:
        return _model, _vectorizer
    if not os.path.exists(MODEL_PATH):
        return None, None
    data = joblib.load(MODEL_PATH)
    _model = data["model"]
    _vectorizer = data["vectorizer"]
    return _model, _vectorizer

def predict_category(description: str, merchant: str = None, amount: float = None, payment_method: str = None):
    model, vectorizer = load_model()
    if model is None:
        return {"category": "Other", "confidence": 0.0, "model_loaded": False}
    text = combine_features(description, merchant, payment_method)
    X = vectorizer.transform([text])
    probs = model.predict_proba(X)[0]
    idx = probs.argmax()
    cat = model.classes_[idx]
    conf = float(probs[idx])
    return {"category": cat, "confidence": round(conf, 4), "model_loaded": True}
