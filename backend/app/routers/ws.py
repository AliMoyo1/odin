import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from app.db import async_session
from app.metrics import ws_connections_active as _ws_active
from app.services.events import _get_async

router = APIRouter(tags=["ws"])
logger = structlog.get_logger(service="ws")

_PING_INTERVAL = 30


async def _consume_ticket(ticket_id: str) -> str | None:
    async with async_session() as session:
        result = await session.execute(
            text(
                "UPDATE ws_tickets SET used = TRUE "
                "WHERE id = :tid AND used = FALSE AND expires_at > CURRENT_TIMESTAMP "
                "RETURNING user_id"
            ),
            {"tid": ticket_id},
        )
        row = result.fetchone()
        if row:
            await session.commit()
            return str(row.user_id)
        return None


async def _redis_to_ws(websocket: WebSocket, pubsub) -> None:
    async for raw_msg in pubsub.listen():
        if raw_msg["type"] == "message":
            try:
                await websocket.send_text(raw_msg["data"])
            except Exception:
                return


async def _relay(websocket: WebSocket, channel: str) -> None:
    r = _get_async()
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    _ws_active.inc()
    redis_task = asyncio.create_task(_redis_to_ws(websocket, pubsub))
    ping_task = asyncio.create_task(_ping_loop(websocket))
    try:
        while True:
            try:
                await websocket.receive()
            except WebSocketDisconnect:
                break
    finally:
        redis_task.cancel()
        ping_task.cancel()
        await asyncio.gather(redis_task, ping_task, return_exceptions=True)
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        _ws_active.dec()


async def _ping_loop(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(_PING_INTERVAL)
        try:
            await websocket.send_text('{"type":"ping"}')
        except Exception:
            return


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket, ticket: str):
    user_id = await _consume_ticket(ticket)
    await websocket.accept()
    if not user_id:
        await websocket.close(code=4401)
        return
    logger.info("ws_events_connected", user_id=user_id)
    await _relay(websocket, f"events:{user_id}")


@router.websocket("/ws/chat/{conversation_id}")
async def ws_chat(websocket: WebSocket, conversation_id: str, ticket: str):
    user_id = await _consume_ticket(ticket)
    await websocket.accept()
    if not user_id:
        await websocket.close(code=4401)
        return

    async with async_session() as session:
        result = await session.execute(
            text("SELECT id FROM conversations WHERE id = :cid AND user_id = :uid"),
            {"cid": conversation_id, "uid": user_id},
        )
        if not result.fetchone():
            await websocket.close(code=4403)
            return

    logger.info("ws_chat_connected", user_id=user_id, conversation_id=conversation_id)
    await _relay(websocket, f"conv:{conversation_id}")
