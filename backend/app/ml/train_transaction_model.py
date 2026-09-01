"""
FinSense Transaction Categorizer Trainer
Supports Kaggle-style CSV with description, merchant, category
Performs: cleaning, lowercasing, missing handling, TF-IDF, train/test split, RandomForest, accuracy evaluation
Saves: model.pkl, vectorizer.pkl, label_encoder.pkl via joblib
Also saves legacy transaction_categorizer.joblib for backward compat
Do NOT train on every FastAPI startup - load once.
"""
import os, pathlib, joblib, pandas as pd, re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

BASE = pathlib.Path(__file__).resolve().parent
DATA_PATHS = [
    BASE / "data" / "training_data.csv",
    BASE.parent.parent / "data" / "training_data.csv",
    pathlib.Path(__file__).resolve().parents[2] / "data" / "training_data.csv",
]
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def clean_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s or "")
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def combine_features(row):
    desc = clean_text(row.get("description",""))
    merch = clean_text(row.get("merchant",""))
    pay = clean_text(row.get("payment_method",""))
    return " ".join([p for p in [desc, merch, pay] if p])

def find_data_file():
    for p in DATA_PATHS:
        if p.exists(): return p
    raise FileNotFoundError(f"Training data not found. Tried: {DATA_PATHS}")

def train():
    data_path = find_data_file()
    print(f"[TRAIN] Loading {data_path}")
    df = pd.read_csv(data_path)
    # Support flexible column names
    df.columns = [c.strip().lower() for c in df.columns]
    # map aliases
    col_map = {"description":["description","narration","details"], "merchant":["merchant","payee"], "category":["category","cat","label"]}
    def resolve(key):
        for alias in col_map[key]:
            if alias in df.columns: return alias
        return None
    c_desc = resolve("description") or "description"
    c_merch = resolve("merchant") or "merchant"
    c_cat = resolve("category") or "category"
    if c_desc not in df.columns or c_cat not in df.columns:
        raise ValueError(f"CSV must contain description and category. Found: {list(df.columns)}")
    # cleaning
    df = df.dropna(subset=[c_cat])
    df[c_desc] = df[c_desc].fillna("")
    if c_merch in df.columns:
        df[c_merch] = df[c_merch].fillna("")
    else:
        df["merchant"] = ""
        c_merch = "merchant"
    if "payment_method" not in df.columns:
        df["payment_method"] = ""
    df["text"] = df.apply(lambda r: combine_features({"description": r[c_desc], "merchant": r[c_merch], "payment_method": r.get("payment_method","")}), axis=1)
    # remove empty text
    df = df[df["text"].str.strip() != ""]
    df[c_cat] = df[c_cat].str.strip()
    # label encoder
    le = LabelEncoder()
    y = le.fit_transform(df[c_cat])
    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1,2), stop_words='english')
    X = vectorizer.fit_transform(df["text"])
    # train/test split - handle rare classes with <2 members
    from collections import Counter
    counts = Counter(y)
    can_stratify = min(counts.values()) >= 2 if counts else False
    strat = y if can_stratify else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=strat)
    model = RandomForestClassifier(n_estimators=150, random_state=42, max_depth=20, n_jobs=-1)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"[TRAIN] Accuracy: {acc:.4f}")
    try:
        print(classification_report(y_test, preds, zero_division=0))
    except Exception as e:
        print(f"report skip {e}")
        print(f"classes: {le.classes_}")
    # save artifacts
    joblib.dump(model, MODEL_DIR / "model.pkl")
    joblib.dump(vectorizer, MODEL_DIR / "vectorizer.pkl")
    joblib.dump(le, MODEL_DIR / "label_encoder.pkl")
    # legacy compat
    joblib.dump({"model": model, "vectorizer": vectorizer, "label_encoder": le}, MODEL_DIR / "transaction_categorizer.joblib")
    print(f"[TRAIN] Saved to {MODEL_DIR}/model.pkl, vectorizer.pkl, label_encoder.pkl and transaction_categorizer.joblib")
    return acc

if __name__ == "__main__":
    train()
