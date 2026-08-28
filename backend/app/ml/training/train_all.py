import os, pandas as pd, joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.linear_model import LinearRegression
import numpy as np

BASE = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE, "..", "data", "training_data.csv")
MODEL_DIR = os.path.join(BASE, "..", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def clean(s):
    import re
    if not isinstance(s,str): s=str(s or "")
    s=s.lower()
    s=re.sub(r'[^a-z0-9 ]',' ',s)
    s=re.sub(r'\s+',' ',s).strip()
    return s

def combine(row):
    return " ".join([clean(row["description"]), clean(row["merchant"]), clean(row["payment_method"])])

def train_categorizer():
    df=pd.read_csv(DATA_PATH)
    df["text"] = df.apply(combine, axis=1)
    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1,2))
    X = vectorizer.fit_transform(df["text"])
    y = df["category"]
    model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=20)
    model.fit(X,y)
    joblib.dump({"model":model, "vectorizer":vectorizer}, os.path.join(MODEL_DIR, "transaction_categorizer.joblib"))
    print("Categorizer trained: ", model.classes_)

def train_forecaster():
    # dummy linear model on synthetic daily spending trend
    X = np.arange(60).reshape(-1,1)
    y = 500 + 10*X.ravel() + np.random.normal(0,50,60)
    model = LinearRegression()
    model.fit(X,y)
    joblib.dump(model, os.path.join(MODEL_DIR, "spending_forecaster.joblib"))
    print("Forecaster trained")

def train_anomaly():
    amounts = np.array([200,300,450,500,600,350,400,480,520,380,420,460,510,390,410]*10).reshape(-1,1)
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(amounts)
    joblib.dump(model, os.path.join(MODEL_DIR, "anomaly_detector.joblib"))
    print("Anomaly detector trained")

if __name__ == "__main__":
    train_categorizer()
    train_forecaster()
    train_anomaly()
    print("All models trained")
