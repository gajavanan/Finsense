from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import date
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Transaction, Notification, AgentInsight
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.api.v1.ws import manager

router = APIRouter()

def to_dict(o):
    d = {c.name: getattr(o,c.name) for c in o.__table__.columns}
    for k,v in list(d.items()):
        if hasattr(v,'isoformat'): d[k]=v.isoformat()
        elif str(type(v)).find('Decimal')!=-1: d[k]=float(v)
    return d

@router.get("/transactions")
async def list_transactions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    category: Optional[str] = None,
    type: Optional[str] = Query(None, alias="type"),
    page: int = 1,
    limit: int = 20,
    sort: str = "date",
    order: str = "desc"
):
    q = db.query(Transaction).filter(Transaction.user_id==user.id)
    if category: q = q.filter(Transaction.category==category)
    if type: q = q.filter(Transaction.type==type)
    if search: q = q.filter(Transaction.description.ilike(f"%{search}%"))
    total = q.count()
    col = getattr(Transaction, sort, Transaction.date)
    if order=="desc": q = q.order_by(col.desc())
    else: q = q.order_by(col.asc())
    items = q.offset((page-1)*limit).limit(limit).all()
    return {"data": [to_dict(x) for x in items], "count": total, "page": page, "limit": limit}

@router.post("/transactions")
async def create_transaction(payload: TransactionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    if not data.get("category"):
        try:
            from app.ml.predictors.categorizer import predict_category
            pred = predict_category(data["description"], data.get("merchant"), data.get("amount"), data.get("payment_method"))
            data["category"] = pred.get("category","Other")
        except: data["category"]="Other"
    tx = Transaction(user_id=user.id, **data)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    # ML anomaly
    try:
        from app.ml.predictors.anomaly import detect_anomaly
        hist = db.query(Transaction.amount).filter(Transaction.user_id==user.id, Transaction.type=="expense").limit(100).all()
        hist_amounts = [float(x[0]) for x in hist]
        anomaly = detect_anomaly(float(data["amount"]), hist_amounts, data.get("category"))
        if anomaly.get("is_anomaly"):
            n = Notification(user_id=user.id, title="Unusual transaction detected", message=f"{data['description']} - {anomaly['reason']}", type="alert")
            db.add(n)
            db.add(AgentInsight(user_id=user.id, title="Anomaly Insight", content=anomaly["reason"], type="anomaly"))
            db.commit()
    except Exception as e:
        print(f"ML pipeline error {e}")
    result = to_dict(tx)
    # websocket broadcast
    try:
        await manager.send_to_user(user.id, "transaction_created", result)
        await manager.send_to_user(user.id, "dashboard_refresh", {})
    except: pass
    return result

@router.put("/transactions/{tid}")
async def update_transaction(tid: str, payload: TransactionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id==tid, Transaction.user_id==user.id).first()
    if not tx: raise HTTPException(404, "Not found")
    for k,v in payload.model_dump(exclude_unset=True).items():
        if v is not None: setattr(tx,k,v)
    db.commit()
    db.refresh(tx)
    try: await manager.send_to_user(user.id, "transaction_updated", to_dict(tx))
    except: pass
    return to_dict(tx)

@router.delete("/transactions/{tid}")
async def delete_transaction(tid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id==tid, Transaction.user_id==user.id).first()
    if not tx: raise HTTPException(404, "Not found")
    db.delete(tx); db.commit()
    try: await manager.send_to_user(user.id, "transaction_deleted", {"id": tid})
    except: pass
    return {"status":"deleted"}
