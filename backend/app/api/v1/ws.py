from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import jwt
from app.core.config import settings
from typing import Dict, List
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: str, ws: WebSocket):
        if user_id in self.active:
            if ws in self.active[user_id]:
                self.active[user_id].remove(ws)
            if not self.active[user_id]:
                del self.active[user_id]

    async def send_to_user(self, user_id: str, event: str, data: dict):
        if user_id in self.active:
            msg = json.dumps({"event": event, "data": data})
            for ws in list(self.active[user_id]):
                try:
                    await ws.send_text(msg)
                except:
                    pass

    async def broadcast(self, event: str, data: dict):
        for uid in list(self.active.keys()):
            await self.send_to_user(uid, event, data)

manager = ConnectionManager()

@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(None)):
    # token via query param ?token=xxx or Authorization header after connect
    if not token:
        # try header
        auth = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ",1)[1]
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008); return
    except Exception:
        await websocket.close(code=1008); return
    await manager.connect(user_id, websocket)
    try:
        # send welcome
        await websocket.send_text(json.dumps({"event":"connected","data":{"user_id":user_id}}))
        while True:
            data = await websocket.receive_text()
            # echo or handle ping
            try:
                obj = json.loads(data)
                if obj.get("event")=="ping":
                    await websocket.send_text(json.dumps({"event":"pong","data":{}}))
            except:
                pass
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
