from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Transaction
from app.schemas.transaction import CategoryPredictRequest, AnomalyRequest, SpendingForecastRequest, BudgetRecommendRequest, GoalPredictRequest
from app.ml.predictors.categorizer import predict_category
from app.ml.predictors.forecaster import forecast_spending
from app.ml.predictors.anomaly import detect_anomaly
from app.ml.predictors.budget_optimizer import recommend_budget
from app.ml.predictors.goal_predictor import predict_goal
import os

router=APIRouter()

@router.post("/ml/predict/category")
async def ml_category(req: CategoryPredictRequest, user: User = Depends(get_current_user)):
    res = predict_category(req.description, req.merchant, req.amount, req.payment_method)
    return res

@router.post("/ml/predict/spending")
async def ml_spending(req: SpendingForecastRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs=db.query(Transaction).filter(Transaction.user_id==user.id, Transaction.type=="expense").order_by(Transaction.date).limit(200).all()
    from collections import defaultdict
    daily=defaultdict(float)
    for t in txs:
        daily[t.date.isoformat()] += float(t.amount)
    sorted_days=sorted(daily.items())
    hist=[{"date":k, "amount":v} for k,v in sorted_days]
    result = forecast_spending(hist, req.period)
    return result

@router.post("/ml/detect/anomaly")
async def ml_anomaly(req: AnomalyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs=db.query(Transaction.amount).filter(Transaction.user_id==user.id, Transaction.type=="expense").limit(100).all()
    hist=[float(x[0]) for x in txs]
    result = detect_anomaly(req.amount, hist, req.category)
    return result

@router.post("/ml/recommend/budget")
async def ml_budget(req: BudgetRecommendRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs=db.query(Transaction).filter(Transaction.user_id==user.id).limit(200).all()
    dicts=[{"type":t.type,"category":t.category,"amount":float(t.amount),"date":t.date.isoformat()} for t in txs]
    res = recommend_budget(dicts, req.income)
    return res

@router.post("/ml/predict/goal")
async def ml_goal(req: GoalPredictRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs=db.query(Transaction).filter(Transaction.user_id==user.id).all()
    hist_rate=None
    try:
        inc=sum(float(t.amount) for t in txs if t.type=="income")
        exp=sum(float(t.amount) for t in txs if t.type=="expense")
        months=len(set([t.date.strftime("%Y-%m") for t in txs])) or 1
        hist_rate=(inc-exp)/months if months else None
    except: pass
    result = predict_goal(req.target_amount, req.current_amount, req.monthly_contribution, hist_rate)
    return result

@router.post("/ml/train")
async def ml_train(user: User = Depends(get_current_user)):
    import pathlib
    base = pathlib.Path(__file__).resolve().parents[3]
    script = base / "app" / "ml" / "training" / "train_all.py"
    try:
        import importlib.util
        spec=importlib.util.spec_from_file_location("train_all", str(script))
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.train_categorizer()
        mod.train_forecaster()
        mod.train_anomaly()
        return {"status":"trained"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/ml/models")
async def ml_models_info():
    base=os.path.join(os.path.dirname(__file__), "..","..","ml","models")
    def exists(n): return os.path.exists(os.path.join(base,n))
    return [
        {"name":"Transaction Categorizer","status":"loaded" if exists("transaction_categorizer.joblib") else "training_required"},
        {"name":"Spending Forecaster","status":"loaded" if exists("spending_forecaster.joblib") else "training_required"},
        {"name":"Anomaly Detector","status":"loaded" if exists("anomaly_detector.joblib") else "training_required"},
        {"name":"Budget Optimizer","status":"loaded"},
        {"name":"Goal Predictor","status":"loaded"},
    ]
