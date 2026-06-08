import asyncio
import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)

_connections: Dict[int, asyncio.Queue] = {}

_HEARTBEAT_INTERVAL = 25.0  # seconds — keeps connections alive through nginx/LB 30s timeouts


async def get_user_queue(user_id: int) -> asyncio.Queue:
    if user_id not in _connections:
        _connections[user_id] = asyncio.Queue()
    return _connections[user_id]


async def remove_user_queue(user_id: int) -> None:
    if user_id in _connections:
        queue = _connections.pop(user_id)
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.info("sse_queue_removed", extra={"user_id": user_id})


async def publish_job_event(user_id: int, job_data: dict) -> None:
    try:
        queue = await get_user_queue(user_id)
        await queue.put(job_data)
        logger.debug("sse_event_published", extra={"user_id": user_id, "status": job_data.get("status")})
    except Exception as exc:
        logger.error("sse_publish_failed", extra={"user_id": user_id, "error": str(exc)})


async def event_generator(user_id: int):
    queue = await get_user_queue(user_id)
    logger.info("sse_client_connected", extra={"user_id": user_id})
    try:
        while True:
            try:
                event_data = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                yield f"data: {json.dumps(event_data)}\n\n"
            except asyncio.TimeoutError:
                # SSE comment line keeps the TCP connection alive through proxies
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        logger.info("sse_client_disconnected", extra={"user_id": user_id})
        raise
    finally:
        await remove_user_queue(user_id)
