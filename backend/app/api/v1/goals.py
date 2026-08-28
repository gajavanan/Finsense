from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Goal
from app.api.v1.ws import manager

router=APIRouter()

class GoalCreate(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0
    target_date: Optional[date]=None
    category: Optional[str]=None

class GoalUpdate(BaseModel):
    name: Optional[str]=None
    target_amount: Optional[float]=None
    current_amount: Optional[float]=None
    target_date: Optional[date]=None

def to_dict(o):
    d={c.name:getattr(o,c.name) for c in o.__table__.columns}
    for k,v in list(d.items()):
        if hasattr(v,'isoformat'): d[k]=v.isoformat()
        elif str(type(v)).find('Decimal')!=-1: d[k]=float(v)
    return d

@router.get("/goals")
async def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goals=db.query(Goal).filter(Goal.user_id==user.id).all()
    return [to_dict(g) for g in goals]

@router.post("/goals")
async def create_goal(payload: GoalCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    g=Goal(user_id=user.id, **payload.model_dump()); db.add(g); db.commit(); db.refresh(g)
    try: await manager.send_to_user(user.id,"goal_created", to_dict(g))
    except: pass
    return to_dict(g)

@router.put("/goals/{gid}")
async def update_goal(gid: str, payload: GoalUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    g=db.query(Goal).filter(Goal.id==gid, Goal.user_id==user.id).first()
    if not g: raise HTTPException(404,"Not found")
    for k,v in payload.model_dump(exclude_unset=True).items():
        if v is not None: setattr(g,k,v)
    db.commit(); db.refresh(g)
    return to_dict(g)

@router.delete("/goals/{gid}")
async def delete_goal(gid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    g=db.query(Goal).filter(Goal.id==gid, Goal.user_id==user.id).first()
    if g: db.delete(g); db.commit()
    return {"status":"deleted"}
