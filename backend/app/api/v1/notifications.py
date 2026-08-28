from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Notification

router=APIRouter()

@router.get("/notifications")
async def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs=db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return [{"id":n.id,"title":n.title,"message":n.message,"type":n.type,"read":n.read,"created_at":n.created_at.isoformat() if n.created_at else None} for n in notifs]

@router.post("/notifications/{nid}/read")
async def mark_read(nid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n=db.query(Notification).filter(Notification.id==nid, Notification.user_id==user.id).first()
    if n: n.read=True; db.commit()
    return {"status":"ok"}
