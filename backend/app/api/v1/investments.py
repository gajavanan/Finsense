from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Asset

router=APIRouter()

class AssetCreate(BaseModel):
    name: str
    symbol: Optional[str]=None
    type: str
    quantity: float
    purchase_price: float
    current_price: Optional[float]=None

def to_dict(o):
    d={c.name:getattr(o,c.name) for c in o.__table__.columns}
    for k,v in list(d.items()):
        if hasattr(v,'isoformat'): d[k]=v.isoformat()
        elif str(type(v)).find('Decimal')!=-1: d[k]=float(v)
    return d

@router.get("/investments")
async def list_assets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assets=db.query(Asset).filter(Asset.user_id==user.id).all()
    out=[]
    for a in assets:
        d=to_dict(a)
        invested=float(a.purchase_price)*float(a.quantity)
        current=float(a.current_price or a.purchase_price)*float(a.quantity)
        pnl=current-invested
        pct= (pnl/invested*100) if invested else 0
        d.update({"invested":round(invested,2), "current_value":round(current,2), "pnl":round(pnl,2), "pct":round(pct,2)})
        out.append(d)
    return out

@router.post("/investments")
async def create_asset(payload: AssetCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data=payload.model_dump()
    if data.get("current_price") is None: data["current_price"]=data["purchase_price"]
    a=Asset(user_id=user.id, **data); db.add(a); db.commit(); db.refresh(a)
    return to_dict(a)
