"""WebSocket endpoint for pipeline progress streaming."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.bus import progress_bus

router = APIRouter()


@router.websocket("/ws/progress/{task_id}")
async def progress_ws(websocket: WebSocket, task_id: str):
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
