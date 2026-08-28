from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Budget, Transaction
from app.api.v1.ws import manager

router = APIRouter()

class BudgetCreate(BaseModel):
    category: str
    amount: float
    period: str = "monthly"
    month: Optional[str] = None

class BudgetUpdate(BaseModel):
    category: Optional[str]=None
    amount: Optional[float]=None
    period: Optional[str]=None

def to_dict(o):
    d={c.name:getattr(o,c.name) for c in o.__table__.columns}
    for k,v in list(d.items()):
        if hasattr(v,'isoformat'): d[k]=v.isoformat()
        elif str(type(v)).find('Decimal')!=-1: d[k]=float(v)
    return d

@router.get("/budgets")
async def list_budgets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    budgets = db.query(Budget).filter(Budget.user_id==user.id).all()
    tx = db.query(Transaction).filter(Transaction.user_id==user.id, Transaction.type=="expense").all()
    cat_spent=defaultdict(float)
    cur = datetime.utcnow().strftime("%Y-%m")
    for t in tx:
        if t.date.strftime("%Y-%m")==cur:
            cat_spent[t.category or "Other"] += float(t.amount)
    out=[]
    for b in budgets:
        spent=cat_spent.get(b.category,0)
        d=to_dict(b); d.update({"spent":spent, "remaining": float(b.amount)-spent, "pct": round(spent/float(b.amount)*100,1) if b.amount else 0})
        out.append(d)
    return out

@router.post("/budgets")
async def create_budget(payload: BudgetCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b=Budget(user_id=user.id, **payload.model_dump()); db.add(b); db.commit(); db.refresh(b)
    try: await manager.send_to_user(user.id,"budget_created", to_dict(b))
    except: pass
    return to_dict(b)

@router.put("/budgets/{bid}")
async def update_budget(bid: str, payload: BudgetUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b=db.query(Budget).filter(Budget.id==bid, Budget.user_id==user.id).first()
    if not b: raise HTTPException(404,"Not found")
    for k,v in payload.model_dump(exclude_unset=True).items():
        if v is not None: setattr(b,k,v)
    db.commit(); db.refresh(b)
    return to_dict(b)

@router.delete("/budgets/{bid}")
async def delete_budget(bid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b=db.query(Budget).filter(Budget.id==bid, Budget.user_id==user.id).first()
    if b: db.delete(b); db.commit()
    return {"status":"deleted"}
