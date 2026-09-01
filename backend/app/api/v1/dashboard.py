from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime, timedelta, date
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Transaction, Budget, Goal, Asset, Notification, AgentInsight, SpendingAlert

router = APIRouter()

def tx_type(t):
    # handle both transaction_type and legacy type
    return getattr(t, 'transaction_type', None) or getattr(t, 'type', None)

@router.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.user_id==user.id).order_by(Transaction.date.desc()).limit(500).all()
    budgets = db.query(Budget).filter(Budget.user_id==user.id).all()
    goals = db.query(Goal).filter(Goal.user_id==user.id).all()
    assets = db.query(Asset).filter(Asset.user_id==user.id).all()
    notifications = db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(5).all()
    insights = db.query(AgentInsight).filter(AgentInsight.user_id==user.id).order_by(AgentInsight.created_at.desc()).limit(5).all()
    alerts = db.query(SpendingAlert).filter(SpendingAlert.user_id==user.id, SpendingAlert.is_read==False).order_by(SpendingAlert.created_at.desc()).limit(5).all()

    def to_dict(o):
        d = {c.name: getattr(o,c.name) for c in o.__table__.columns}
        for k,v in list(d.items()):
            if hasattr(v,'isoformat'):
                d[k]=v.isoformat()
            elif isinstance(v, (int,float)) == False and str(type(v)).find('Decimal')!=-1:
                d[k]=float(v)
        # alias for transaction
        if "transaction_type" in d and d.get("transaction_type"):
            d["type"] = d["transaction_type"]
        elif d.get("type") and not d.get("transaction_type"):
            d["transaction_type"] = d["type"]
        if "monthly_limit" in d and d.get("monthly_limit") is None and d.get("amount") is not None:
            d["monthly_limit"] = float(d["amount"])
        return d

    tx_dicts = [to_dict(t) for t in txs]
    now = datetime.utcnow()
    today = now.date()
    month_start = now.replace(day=1).date()
    # handle both transaction_type and type
    monthly_income = sum(float(t.amount) for t in txs if tx_type(t)=="income" and t.date >= month_start)
    monthly_expenses = sum(float(t.amount) for t in txs if tx_type(t)=="expense" and t.date >= month_start)
    total_balance = sum(float(t.amount) if tx_type(t)=="income" else -float(t.amount) for t in txs if tx_type(t) in ["income","expense"])
    # Savings
    monthly_savings = monthly_income - monthly_expenses
    savings_rate = round((monthly_savings/monthly_income*100) if monthly_income>0 else 0,1)
    # Today's spending
    todays_spending = sum(float(t.amount) for t in txs if tx_type(t)=="expense" and t.date == today)
    net_worth = total_balance + sum(float(a.current_price or a.purchase_price or 0)*float(a.quantity) for a in assets)

    cat_spent = defaultdict(float)
    for t in txs:
        if tx_type(t)=="expense" and t.date.strftime("%Y-%m")==now.strftime("%Y-%m"):
            cat_spent[t.category or "Other"] += float(t.amount)
    budget_usage=[]
    for b in budgets:
        spent=cat_spent.get(b.category,0)
        limit = float(b.monthly_limit if b.monthly_limit is not None else b.amount)
        pct= round(spent/limit*100,1) if limit else 0
        budget_usage.append({**to_dict(b), "spent": spent, "remaining": limit-spent, "pct": pct, "monthly_limit": limit})

    score=50
    if savings_rate>20: score+=20
    elif savings_rate>10: score+=10
    if monthly_expenses < monthly_income: score+=10
    if len([b for b in budget_usage if b["pct"]<100])> len(budget_usage)/2 if budget_usage else False: score+=10
    if len(goals)>0: score+=10
    score=min(100, score)

    trend=[]
    for i in range(5,-1,-1):
        d = (now - timedelta(days=30*i))
        key = d.strftime("%Y-%m")
        inc = sum(float(t.amount) for t in txs if tx_type(t)=="income" and t.date.strftime("%Y-%m")==key)
        exp = sum(float(t.amount) for t in txs if tx_type(t)=="expense" and t.date.strftime("%Y-%m")==key)
        trend.append({"month": key, "income": inc, "expenses": exp})
    breakdown = [{"category":k, "amount":round(v,2)} for k,v in cat_spent.items()]

    # spending alerts already in alerts
    return {
        "total_balance": round(total_balance,2),
        "balance": round(total_balance,2),
        "net_worth": round(net_worth,2),
        "monthly_income": round(monthly_income,2),
        "monthly_expenses": round(monthly_expenses,2),
        "monthly_savings": round(monthly_savings,2),
        "savings": round(monthly_savings,2),
        "savings_rate": savings_rate,
        "todays_spending": round(todays_spending,2),
        "todaysSpending": round(todays_spending,2),
        "budget_usage": budget_usage,
        "active_goals": [to_dict(g) for g in goals],
        "recent_transactions": tx_dicts[:10],
        "assets": [to_dict(a) for a in assets],
        "notifications": [to_dict(n) for n in notifications],
        "insights": [to_dict(i) for i in insights],
        "alerts": [to_dict(a) for a in alerts],
        "spending_alerts": [to_dict(a) for a in alerts],
        "health_score": score,
        "spending_trend": trend,
        "monthly_spending_trend": trend,
        "category_breakdown": breakdown,
        "category_wise_spending": breakdown,
        "health_details": {
            "score": score,
            "strengths": ["Good savings rate" if savings_rate>15 else "Budget tracking active", "Expense tracking" if len(txs)>5 else "Add more data"],
            "improvements": ["High subscription spending" if cat_spent.get("Subscriptions",0)>1000 else "Keep monitoring budgets"]
        }
    }
