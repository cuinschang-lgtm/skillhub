"""WebSocket endpoint for pipeline progress streaming."""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from starlette.responses import Response

from app.db import SessionLocal
from app.models import Task
from app.security import decode_access_token
from app.ws.bus import progress_bus

router = APIRouter()


async def _deny(websocket: WebSocket) -> bool:
    await websocket.send_denial_response(Response(status_code=403))
    return False


async def _authorize_progress_subscription(websocket: WebSocket, task_id: str) -> bool:
    token = (websocket.query_params.get("token") or "").strip()
    if not token:
        return await _deny(websocket)

    try:
        payload = decode_access_token(token)
        task_uuid = uuid.UUID(task_id)
    except (HTTPException, ValueError):
        return await _deny(websocket)

    async with SessionLocal() as session:
        result = await session.execute(select(Task.user_id).where(Task.id == task_uuid))
        owner_id = result.scalar_one_or_none()

    if owner_id != payload.user_id:
        return await _deny(websocket)
    return True


@router.websocket("/ws/progress/{task_id}")
async def progress_ws(websocket: WebSocket, task_id: str):
    if not await _authorize_progress_subscription(websocket, task_id):
        return

    await websocket.accept()
    queue = progress_bus.subscribe(task_id)

    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    finally:
        progress_bus.unsubscribe(task_id, queue)
