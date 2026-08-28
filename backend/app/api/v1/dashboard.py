from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Transaction, Budget, Goal, Asset, Notification, AgentInsight

router = APIRouter()

@router.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.user_id==user.id).order_by(Transaction.date.desc()).limit(200).all()
    budgets = db.query(Budget).filter(Budget.user_id==user.id).all()
    goals = db.query(Goal).filter(Goal.user_id==user.id).all()
    assets = db.query(Asset).filter(Asset.user_id==user.id).all()
    notifications = db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(5).all()
    insights = db.query(AgentInsight).filter(AgentInsight.user_id==user.id).order_by(AgentInsight.created_at.desc()).limit(5).all()

    def to_dict(o):
        d = {c.name: getattr(o,c.name) for c in o.__table__.columns}
        for k,v in list(d.items()):
            if hasattr(v,'isoformat'):
                d[k]=v.isoformat()
            elif isinstance(v, (int,float)) == False and str(type(v)).find('Decimal')!=-1:
                d[k]=float(v)
        return d

    tx_dicts = [to_dict(t) for t in txs]
    now = datetime.utcnow()
    month_start = now.replace(day=1).date()
    monthly_income = sum(float(t.amount) for t in txs if t.type=="income" and t.date >= month_start)
    monthly_expenses = sum(float(t.amount) for t in txs if t.type=="expense" and t.date >= month_start)
    total_balance = sum(float(t.amount) if t.type=="income" else -float(t.amount) for t in txs if t.type in ["income","expense"])
    net_worth = total_balance + sum(float(a.current_price or a.purchase_price or 0)*float(a.quantity) for a in assets)
    savings_rate = round(((monthly_income - monthly_expenses)/monthly_income*100) if monthly_income>0 else 0,1)

    cat_spent = defaultdict(float)
    for t in txs:
        if t.type=="expense" and t.date.strftime("%Y-%m")==now.strftime("%Y-%m"):
            cat_spent[t.category or "Other"] += float(t.amount)
    budget_usage=[]
    for b in budgets:
        spent=cat_spent.get(b.category,0)
        amt=float(b.amount)
        pct= round(spent/amt*100,1) if amt else 0
        budget_usage.append({**to_dict(b), "spent": spent, "remaining": amt-spent, "pct": pct})

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
        inc = sum(float(t.amount) for t in txs if t.type=="income" and t.date.strftime("%Y-%m")==key)
        exp = sum(float(t.amount) for t in txs if t.type=="expense" and t.date.strftime("%Y-%m")==key)
        trend.append({"month": key, "income": inc, "expenses": exp})
    breakdown = [{"category":k, "amount":v} for k,v in cat_spent.items()]

    return {
        "total_balance": round(total_balance,2),
        "net_worth": round(net_worth,2),
        "monthly_income": round(monthly_income,2),
        "monthly_expenses": round(monthly_expenses,2),
        "savings_rate": savings_rate,
        "budget_usage": budget_usage,
        "active_goals": [to_dict(g) for g in goals],
        "recent_transactions": tx_dicts[:10],
        "assets": [to_dict(a) for a in assets],
        "notifications": [to_dict(n) for n in notifications],
        "insights": [to_dict(i) for i in insights],
        "health_score": score,
        "spending_trend": trend,
        "category_breakdown": breakdown,
        "health_details": {
            "score": score,
            "strengths": ["Good savings rate" if savings_rate>15 else "Budget tracking active", "Expense tracking" if len(txs)>5 else "Add more data"],
            "improvements": ["High subscription spending" if cat_spent.get("Subscriptions",0)>1000 else "Keep monitoring budgets"]
        }
    }
