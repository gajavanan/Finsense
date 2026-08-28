from fastapi import APIRouter, Depends, Query
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Transaction

router=APIRouter()

def build_report(txs, period):
    inc=sum(float(t.amount) for t in txs if t.type=="income")
    exp=sum(float(t.amount) for t in txs if t.type=="expense")
    cat=defaultdict(float)
    merchants=defaultdict(float)
    for t in txs:
        if t.type=="expense":
            cat[t.category or "Other"] += float(t.amount)
            merchants[t.merchant or t.description or "Unknown"] += float(t.amount)
    top_merchants=sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "period": period,
        "income": round(inc,2),
        "expenses": round(exp,2),
        "savings": round(inc-exp,2),
        "category_breakdown": [{"category":k,"amount":round(v,2)} for k,v in cat.items()],
        "top_merchants": [{"merchant":k,"amount":round(v,2)} for k,v in top_merchants],
        "transaction_count": len(txs)
    }

@router.get("/reports/monthly")
async def monthly_report(month: str = Query(None, description="YYYY-MM"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not month: month=datetime.utcnow().strftime("%Y-%m")
    txs=db.query(Transaction).filter(Transaction.user_id==user.id).all()
    filtered=[t for t in txs if t.date.strftime("%Y-%m")==month]
    return build_report(filtered, month)

@router.get("/reports/annual")
async def annual_report(year: str = Query(None, description="YYYY"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not year: year=str(datetime.utcnow().year)
    txs=db.query(Transaction).filter(Transaction.user_id==user.id).all()
    filtered=[t for t in txs if str(t.date.year)==year]
    monthly=[]
    for m in range(1,13):
        key=f"{year}-{m:02d}"
        mtx=[t for t in filtered if t.date.strftime("%Y-%m")==key]
        inc=sum(float(t.amount) for t in mtx if t.type=="income")
        exp=sum(float(t.amount) for t in mtx if t.type=="expense")
        monthly.append({"month":key, "income":inc, "expenses":exp})
    base=build_report(filtered, year)
    base["monthly_trend"]=monthly
    return base
