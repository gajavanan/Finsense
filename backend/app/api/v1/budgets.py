from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Budget, Transaction, SpendingAlert, Notification
from app.api.v1.ws import manager
import uuid

router = APIRouter()

class BudgetCreate(BaseModel):
    category: str
    monthly_limit: Optional[float] = None
    amount: Optional[float] = None  # legacy alias
    period: str = "monthly"
    month: Optional[str] = None
    year: Optional[str] = None

    @field_validator('monthly_limit', 'amount')
    @classmethod
    def positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Limit must be positive')
        return v

    def get_limit(self):
        # priority monthly_limit else amount
        val = self.monthly_limit if self.monthly_limit is not None else self.amount
        if val is None:
            raise ValueError('monthly_limit or amount required')
        return val

class BudgetUpdate(BaseModel):
    category: Optional[str]=None
    monthly_limit: Optional[float]=None
    amount: Optional[float]=None
    period: Optional[str]=None
    month: Optional[str]=None
    year: Optional[str]=None

def to_dict(o):
    d={c.name:getattr(o,c.name) for c in o.__table__.columns}
    for k,v in list(d.items()):
        if hasattr(v,'isoformat'): d[k]=v.isoformat()
        elif str(type(v)).find('Decimal')!=-1: d[k]=float(v)
    # alias for frontend compat
    if d.get("monthly_limit") is None and d.get("amount") is not None:
        d["monthly_limit"] = float(d["amount"])
    if d.get("amount") is None and d.get("monthly_limit") is not None:
        d["amount"] = float(d["monthly_limit"])
    # ensure month/year
    if not d.get("month"):
        d["month"] = datetime.utcnow().strftime("%m")
    if not d.get("year"):
        d["year"] = datetime.utcnow().strftime("%Y")
    return d

@router.get("/budgets")
async def list_budgets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    budgets = db.query(Budget).filter(Budget.user_id==user.id).all()
    tx = db.query(Transaction).filter(Transaction.user_id==user.id, Transaction.transaction_type=="expense").all()
    # fallback for legacy type
    if not tx:
        tx = db.query(Transaction).filter(Transaction.user_id==user.id, Transaction.type=="expense").all()
    cat_spent=defaultdict(float)
    cur = datetime.utcnow().strftime("%Y-%m")
    for t in tx:
        try:
            if t.date.strftime("%Y-%m")==cur:
                cat_spent[t.category or "Other"] += float(t.amount)
        except: pass
    out=[]
    for b in budgets:
        limit = float(b.monthly_limit if b.monthly_limit is not None else b.amount)
        spent=cat_spent.get(b.category,0)
        d=to_dict(b); d.update({"spent":spent, "remaining": limit-spent, "pct": round(spent/limit*100,1) if limit else 0, "monthly_limit": limit})
        out.append(d)
    return out

@router.post("/budgets")
async def create_budget(payload: BudgetCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limit = payload.get_limit()
    now = datetime.utcnow()
    month = payload.month or now.strftime("%m")
    year = payload.year or now.strftime("%Y")
    # normalize month to 2-digit
    if len(month)==1: month="0"+month
    if "-" in month:  # if passed as YYYY-MM
        parts = month.split("-")
        if len(parts)==2:
            year, month = parts[0], parts[1]
    data = {
        "category": payload.category,
        "amount": limit,
        "monthly_limit": limit,
        "period": payload.period,
        "month": month,
        "year": year
    }
    b=Budget(id=str(uuid.uuid4()), user_id=user.id, **data)
    db.add(b); db.commit(); db.refresh(b)
    try: await manager.send_to_user(user.id,"budget_created", to_dict(b))
    except: pass
    return to_dict(b)

@router.put("/budgets/{bid}")
async def update_budget(bid: str, payload: BudgetUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b=db.query(Budget).filter(Budget.id==bid, Budget.user_id==user.id).first()
    if not b: raise HTTPException(404,"Not found")
    updates = payload.model_dump(exclude_unset=True)
    # handle monthly_limit/amount alias
    if "monthly_limit" in updates and updates["monthly_limit"] is not None:
        b.monthly_limit = updates["monthly_limit"]
        b.amount = updates["monthly_limit"]
    elif "amount" in updates and updates["amount"] is not None:
        b.amount = updates["amount"]
        b.monthly_limit = updates["amount"]
    for k in ["category","period","month","year"]:
        if k in updates and updates[k] is not None:
            setattr(b,k,updates[k])
    b.updated_at = datetime.utcnow()
    db.commit(); db.refresh(b)
    return to_dict(b)

@router.delete("/budgets/{bid}")
async def delete_budget(bid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b=db.query(Budget).filter(Budget.id==bid, Budget.user_id==user.id).first()
    if not b: raise HTTPException(404,"Not found")
    db.delete(b); db.commit()
    return {"status":"deleted"}

# Spending alerts endpoints per Phase 9
@router.get("/budgets/alerts")
@router.get("/alerts")
async def list_alerts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerts = db.query(SpendingAlert).filter(SpendingAlert.user_id==user.id).order_by(SpendingAlert.created_at.desc()).limit(20).all()
    def a_dict(o):
        d={c.name:getattr(o,c.name) for c in o.__table__.columns}
        for k,v in list(d.items()):
            if hasattr(v,'isoformat'): d[k]=v.isoformat()
            elif str(type(v)).find('Decimal')!=-1: d[k]=float(v)
        return d
    return [a_dict(a) for a in alerts]

@router.put("/alerts/{aid}/read")
async def mark_read(aid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a=db.query(SpendingAlert).filter(SpendingAlert.id==aid, SpendingAlert.user_id==user.id).first()
    if not a: raise HTTPException(404,"Not found")
    a.is_read=True; db.commit()
    return {"status":"read"}
