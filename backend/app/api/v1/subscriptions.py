from fastapi import APIRouter, Depends
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Transaction

router=APIRouter()

@router.get("/subscriptions")
async def detect_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs=db.query(Transaction).filter(Transaction.user_id==user.id).order_by(Transaction.date).all()
    groups=defaultdict(list)
    for t in txs:
        key=(t.merchant or t.description or "").lower().strip()
        groups[key].append(t)
    subs=[]
    for merchant, items in groups.items():
        if len(items) >= 2:
            amounts=[float(x.amount) for x in items]
            avg=sum(amounts)/len(amounts)
            try:
                last = max(items, key=lambda x: x.date)
                next_date= last.date + timedelta(days=30)
                subs.append({"merchant": merchant or last.merchant or last.description, "count": len(items), "avg_amount": round(avg,2), "frequency":"monthly", "next_expected": next_date.isoformat(), "last_date": last.date.isoformat()})
            except: pass
    keywords=["netflix","spotify","prime","youtube","hotstar","sip","rent","insurance","apple","google","adobe","notion","chatgpt","openai"]
    filtered=[s for s in subs if any(k in s["merchant"].lower() for k in keywords) or s["count"]>=3]
    return filtered
