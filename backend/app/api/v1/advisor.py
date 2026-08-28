from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Transaction, Budget, Goal, ChatMessage
from app.services.advisor_service import chat_with_advisor

router=APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]]=None

@router.post("/advisor/chat")
async def advisor_chat(payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await chat_with_advisor(user.id, payload.message, payload.history, db)
    try:
        db.add(ChatMessage(user_id=user.id, role="user", content=payload.message))
        db.add(ChatMessage(user_id=user.id, role="assistant", content=result["response"]))
        db.commit()
    except Exception as e:
        print(f"chat store failed {e}")
    return result

@router.get("/advisor/history")
async def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msgs=db.query(ChatMessage).filter(ChatMessage.user_id==user.id).order_by(ChatMessage.created_at).limit(50).all()
    return [{"id":m.id,"role":m.role,"content":m.content,"created_at":m.created_at.isoformat() if m.created_at else None} for m in msgs]
