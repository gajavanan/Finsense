from app.ml.predictors.categorizer import predict_category
from app.ml.predictors.anomaly import detect_anomaly
from app.ml.predictors.budget_optimizer import recommend_budget
from app.ml.predictors.goal_predictor import predict_goal

def test_categorizer_fallback():
    r=predict_category("Swiggy food order", "Swiggy", 400)
    assert "category" in r

def test_anomaly_insufficient():
    r=detect_anomaly(1000, [])
    assert "is_anomaly" in r

def test_budget_insufficient():
    r=recommend_budget([])
    assert r["status"]=="insufficient_data"

def test_goal():
    r=predict_goal(100000, 20000, 5000)
    assert r["status"]=="success"
    assert r["months"]>0
