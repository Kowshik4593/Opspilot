import asyncio
import json
from typing import AsyncGenerator

# Simple in-memory event queue for agent events and processing traces.
# Producers call `push_event`, consumers use `event_generator` to stream.

events_queue: asyncio.Queue = asyncio.Queue()

async def push_event(event: dict) -> None:
    await events_queue.put(event)

async def event_generator() -> AsyncGenerator[str, None]:
    # yields JSON-serialized events as strings for SSE
    while True:
        ev = await events_queue.get()
        try:
            yield json.dumps(ev)
        finally:
            events_queue.task_done()
