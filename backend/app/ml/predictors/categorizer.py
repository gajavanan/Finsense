import os
from pathlib import Path
import joblib
import numpy as np
from app.ml.preprocessing.text_features import clean_text, extract_merchant, preprocess_bank_description, combine_features

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = str(_MODELS_DIR / "transaction_categorizer.joblib")
MODEL_PKL = str(_MODELS_DIR / "model.pkl")
VECTORIZER_PKL = str(_MODELS_DIR / "vectorizer.pkl")
LABEL_ENCODER_PKL = str(_MODELS_DIR / "label_encoder.pkl")

_model = None
_vectorizer = None
_label_encoder = None

# Comprehensive Rule-Based Merchant & Keyword Mapping
MERCHANT_RULES = {
    # Food
    "swiggy": "Food",
    "zomato": "Food",
    "a2b": "Food",
    "adayar ananda bhavan": "Food",
    "restaurant": "Food",
    "restaurants": "Food",
    "hotel": "Food",
    "hotel ": "Food",
    "hot ": "Food",  # covers "SHAKTHI VELAN HOT"
    "cafe": "Food",
    "bakery": "Food",
    "bhavan": "Food",
    "dhaba": "Food",
    "mess": "Food",
    "biryani": "Food",
    "pizza": "Food",
    "burger": "Food",
    "tea": "Food",
    "coffee": "Food",
    "canteen": "Food",
    "juice": "Food",
    "chicken": "Food",
    "mutton": "Food",
    "meat": "Food",
    "sweet": "Food",
    "sweets": "Food",
    "fast food": "Food",
    "dine": "Food",
    "food": "Food",
    "dominos": "Food",
    "domino": "Food",
    "mcdonald": "Food",
    "kfc": "Food",
    "starbucks": "Food",

    # Shopping
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "myntra": "Shopping",
    "meesho": "Shopping",
    "ajio": "Shopping",
    "nykaa": "Shopping",
    "tata cliq": "Shopping",
    "croma": "Shopping",
    "reliance digital": "Shopping",
    "dmart": "Shopping",
    "relianceretail": "Shopping",
    "reliance fresh": "Shopping",
    "stores": "Shopping",
    "store": "Shopping",
    "traders": "Shopping",
    "bazaar": "Shopping",
    "mart": "Shopping",
    "supermarket": "Shopping",
    "retail": "Shopping",
    "textiles": "Shopping",
    "silks": "Shopping",
    "readymade": "Shopping",
    "fashion": "Shopping",
    "garments": "Shopping",
    "fancy": "Shopping",
    "maligai": "Shopping",
    "provision": "Shopping",
    "copiers": "Shopping",
    "xerox": "Shopping",

    # Transport
    "uber": "Transport",
    "ola": "Transport",
    "rapido": "Transport",
    "indian oil": "Transport",
    "hp petrol": "Transport",
    "bharat petroleum": "Transport",
    "ioc": "Transport",
    "iocl": "Transport",
    "bpcl": "Transport",
    "hpcl": "Transport",
    "petrol": "Transport",
    "fuel": "Transport",
    "diesel": "Transport",
    "auto": "Transport",
    "cab": "Transport",
    "metro": "Transport",
    "toll": "Transport",
    "fastag": "Transport",

    # Bills
    "tangedco": "Bills",
    "tneb": "Bills",
    "electricity": "Bills",
    "bescom": "Bills",
    "cesc": "Bills",
    "airtel": "Bills",
    "jio": "Bills",
    "vodafone": "Bills",
    "vi ": "Bills",
    "act fibernet": "Bills",
    "hathway": "Bills",
    "broadband": "Bills",
    "dth": "Bills",
    "tata sky": "Bills",
    "tataplay": "Bills",
    "sun direct": "Bills",
    "gas": "Bills",
    "indane": "Bills",
    "bharat gas": "Bills",
    "hp gas": "Bills",
    "water": "Bills",
    "municipal": "Bills",
    "property tax": "Bills",
    "eb": "Bills",

    # Subscriptions
    "netflix": "Subscriptions",
    "spotify": "Subscriptions",
    "prime video": "Subscriptions",
    "amazon prime": "Subscriptions",
    "hotstar": "Subscriptions",
    "disney": "Subscriptions",
    "youtube": "Subscriptions",
    "apple.com/bill": "Subscriptions",
    "google storage": "Subscriptions",
    "chatgpt": "Subscriptions",
    "openai": "Subscriptions",
    "github": "Subscriptions",
    "medium": "Subscriptions",
    "playstation": "Subscriptions",
    "xbox": "Subscriptions",
    "subscription": "Subscriptions",

    # Healthcare
    "apollo": "Healthcare",
    "apollo pharmacy": "Healthcare",
    "medplus": "Healthcare",
    "netmeds": "Healthcare",
    "pharmeasy": "Healthcare",
    "1mg": "Healthcare",
    "pharmacy": "Healthcare",
    "medical": "Healthcare",
    "hospital": "Healthcare",
    "clinic": "Healthcare",
    "diagnostic": "Healthcare",
    "dr.": "Healthcare",
    "doctor": "Healthcare",
    "lab": "Healthcare",
    "pathology": "Healthcare",
    "healthcare": "Healthcare",
    "dental": "Healthcare",

    # Education
    "udemy": "Education",
    "coursera": "Education",
    "unacademy": "Education",
    "byju": "Education",
    "byjus": "Education",
    "simplilearn": "Education",
    "college": "Education",
    "school": "Education",
    "university": "Education",
    "institute": "Education",
    "academy": "Education",
    "classes": "Education",
    "tuition": "Education",
    "education": "Education",
    "course": "Education",
    "fees": "Education",
    "book": "Education",
    "books": "Education",
    "stationary": "Education",

    # Travel
    "irctc": "Travel",
    "indigo": "Travel",
    "air india": "Travel",
    "spicejet": "Travel",
    "akasa": "Travel",
    "makemytrip": "Travel",
    "goibibo": "Travel",
    "yatra": "Travel",
    "easemytrip": "Travel",
    "cleartrip": "Travel",
    "redbus": "Travel",
    "abhibus": "Travel",
    "booking.com": "Travel",
    "agoda": "Travel",
    "airbnb": "Travel",
    "flight": "Travel",
    "travel": "Travel",
    "train": "Travel",
    "bus": "Travel",
    "ticket": "Travel",

    # Investment
    "groww": "Investment",
    "zerodha": "Investment",
    "upstox": "Investment",
    "angel one": "Investment",
    "5paisa": "Investment",
    "kite": "Investment",
    "coin": "Investment",
    "mutual fund": "Investment",
    "sip": "Investment",
    "nse": "Investment",
    "bse": "Investment",
    "sebi": "Investment",
    "investment": "Investment",
    "shares": "Investment",
    "stock": "Investment",
    "securities": "Investment",

    # Rent
    "rent": "Rent",
    "landlord": "Rent",
    "house rent": "Rent",
    "pg rent": "Rent",
    "flat rent": "Rent",

    # Entertainment
    "pvr": "Entertainment",
    "inox": "Entertainment",
    "cinepolis": "Entertainment",
    "bookmyshow": "Entertainment",
    "movie": "Entertainment",
    "theatre": "Entertainment",
    "cinema": "Entertainment",
    "gaming": "Entertainment",
    "amusement": "Entertainment",
}

CONFIDENCE_THRESHOLD = 0.55

def _rule_based(description: str, merchant: str = None):
    texts_to_check = []
    if merchant:
        texts_to_check.append(str(merchant).lower())
    if description:
        texts_to_check.append(str(description).lower())
    for text in texts_to_check:
        for key, cat in MERCHANT_RULES.items():
            if key in text:
                return cat
    return None

def load_model():
    global _model, _vectorizer, _label_encoder
    if _model is not None:
        return _model, _vectorizer, _label_encoder
    if os.path.exists(MODEL_PKL) and os.path.exists(VECTORIZER_PKL):
        try:
            _model = joblib.load(MODEL_PKL)
            _vectorizer = joblib.load(VECTORIZER_PKL)
            if os.path.exists(LABEL_ENCODER_PKL):
                _label_encoder = joblib.load(LABEL_ENCODER_PKL)
            return _model, _vectorizer, _label_encoder
        except Exception as e:
            print(f"[load_model] load model.pkl failed: {e}")
    if os.path.exists(MODEL_PATH):
        try:
            data = joblib.load(MODEL_PATH)
            if isinstance(data, dict) and "model" in data:
                _model = data["model"]
                _vectorizer = data["vectorizer"]
                _label_encoder = data.get("label_encoder")
            else:
                _model = data
            return _model, _vectorizer, _label_encoder
        except Exception as e:
            print(f"[load_model] load transaction_categorizer.joblib failed: {e}")
    return None, None, None

def predict_category(description: str, merchant: str = None, amount: float = None, payment_method: str = None):
    return categorize_transaction(description, merchant, amount, payment_method)

def categorize_transaction(description: str, merchant: str = None, amount: float = None, payment_method: str = None):
    """
    Hybrid system:
      1. Preprocess description and extract merchant
      2. Rule-based merchant mapping
      3. ML prediction with OOV and confidence check
      4. Other fallback
    """
    preprocessed = preprocess_bank_description(description)
    extracted_merchant = merchant or preprocessed.get("merchant") or ""
    clean_desc = preprocessed.get("clean_text") or clean_text(description)
    inferred_payment = payment_method or preprocessed.get("payment_method") or ""

    # 1. Rule-based check
    rule_cat = _rule_based(clean_desc, extracted_merchant)
    if not rule_cat:
        rule_cat = _rule_based(description, extracted_merchant)

    if rule_cat:
        return {
            "category": rule_cat,
            "confidence": 0.95,
            "merchant": extracted_merchant,
            "model_loaded": False,
            "method": "rule"
        }

    # 2. ML Prediction
    model, vectorizer, label_encoder = load_model()
    if model is None or vectorizer is None:
        return {
            "category": "Other",
            "confidence": 0.0,
            "merchant": extracted_merchant,
            "model_loaded": False,
            "method": "fallback"
        }

    text = combine_features(clean_desc, extracted_merchant, inferred_payment)
    if not text.strip():
        return {
            "category": "Other",
            "confidence": 0.0,
            "merchant": extracted_merchant,
            "model_loaded": True,
            "method": "ml_empty"
        }

    try:
        X = vectorizer.transform([text])
        # If all tokens are Out-Of-Vocabulary (e.g. personal names), return Other with 0 confidence
        if X.nnz == 0:
            return {
                "category": "Other",
                "confidence": 0.0,
                "merchant": extracted_merchant,
                "model_loaded": True,
                "method": "ml_oov"
            }

        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)[0]
            idx = probs.argmax()
            raw_class = model.classes_[idx]
            conf = float(probs[idx])
        else:
            raw_class = model.predict(X)[0]
            conf = 0.7

        cat = raw_class
        if label_encoder is not None and isinstance(raw_class, (int, np.integer)):
            try:
                cat = label_encoder.inverse_transform([raw_class])[0]
            except Exception:
                pass

        if conf < CONFIDENCE_THRESHOLD:
            return {
                "category": "Other",
                "confidence": round(conf, 4),
                "merchant": extracted_merchant,
                "model_loaded": True,
                "method": "ml_low_conf"
            }

        return {
            "category": str(cat),
            "confidence": round(conf, 4),
            "merchant": extracted_merchant,
            "model_loaded": True,
            "method": "ml"
        }
    except Exception as e:
        print(f"[categorize_transaction] ML inference failed: {e}")
        return {
            "category": "Other",
            "confidence": 0.0,
            "merchant": extracted_merchant,
            "model_loaded": True,
            "method": "ml_error"
        }

