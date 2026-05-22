import asyncio
import json
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# Module-level dict to store queues per user_id
# Format: {user_id: asyncio.Queue}
_connections: Dict[int, asyncio.Queue] = {}


async def get_user_queue(user_id: int) -> asyncio.Queue:
    """Get or create a queue for a specific user"""
    if user_id not in _connections:
        _connections[user_id] = asyncio.Queue()
    return _connections[user_id]


async def remove_user_queue(user_id: int):
    """Remove a user's queue when they disconnect"""
    if user_id in _connections:
        queue = _connections.pop(user_id)
        # Clear any remaining messages in the queue
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.info(f"Removed SSE queue for user {user_id}")


async def publish_job_event(user_id: int, job_data: dict):
    """Publish a job event to a user's queue"""
    try:
        queue = await get_user_queue(user_id)
        await queue.put(job_data)
        logger.debug(f"Published event for user {user_id}: {job_data}")
    except Exception as e:
        logger.error(f"Error publishing event for user {user_id}: {e}")


async def event_generator(user_id: int):
    """Generator function for SSE events"""
    queue = await get_user_queue(user_id)
    
    try:
        while True:
            # Wait for an event from the queue
            event_data = await queue.get()
            
            # Format as SSE message
            event_str = f"data: {json.dumps(event_data)}\n\n"
            yield event_str
            
    except asyncio.CancelledError:
        logger.info(f"SSE connection cancelled for user {user_id}")
        raise
    finally:
        await remove_user_queue(user_id)
