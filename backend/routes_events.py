from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from backend import events
from typing import Dict
import json

router = APIRouter()

@router.get('/events')
async def stream_events(request: Request):
    async def gen():
        async for ev in events.event_generator():
            # client disconnected
            if await request.is_disconnected():
                break
            yield ev

    return EventSourceResponse(gen())

@router.post('/events')
async def post_event(payload: Dict):
    await events.push_event(payload)
    return {"status": "queued"}
