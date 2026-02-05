from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from typing import List
from pathlib import Path
from backend import repo_adapter
import json

router = APIRouter()

ROOT = Path(__file__).resolve().parents[1]

@router.get('/meetings')
async def list_meetings():
    return await repo_adapter.get_meetings()

@router.get('/meetings/{meeting_id}')
async def get_meeting(meeting_id: str):
    meetings = await repo_adapter.get_meetings()
    m = next((x for x in meetings if x.get('meeting_id') == meeting_id), None)
    if not m:
        raise HTTPException(status_code=404, detail='Meeting not found')
    return m

@router.get('/meetings/{meeting_id}/mom')
async def get_meeting_mom(meeting_id: str):
    """Get Minutes of Meeting for a specific meeting"""
    # Try to find MoM from mom.json file
    possible_paths = [
        ROOT / "data" / "mock_data_json" / "calendar" / "mom.json",
        ROOT / "frontend" / "public" / "data" / "meetings" / "mom.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            try:
                moms = json.loads(path.read_text(encoding="utf-8"))
                mom = next((m for m in moms if m.get('meeting_id') == meeting_id), None)
                if mom:
                    return mom
            except:
                continue
    
    # Also try individual meeting MoM file
    mom_paths = [
        ROOT / "data" / "mock_data_json" / "calendar" / "mom" / f"{meeting_id}.json",
        ROOT / "frontend" / "public" / "data" / "meetings" / "mom" / f"{meeting_id}.json",
    ]
    
    for path in mom_paths:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except:
                continue
    
    return None

@router.get('/meetings/{meeting_id}/transcript')
async def get_meeting_transcript(meeting_id: str):
    """Get transcript for a specific meeting"""
    # First get the meeting to find transcript filename
    meetings = await repo_adapter.get_meetings()
    meeting = next((m for m in meetings if m.get('meeting_id') == meeting_id), None)
    
    if not meeting:
        raise HTTPException(status_code=404, detail='Meeting not found')
    
    transcript_file = meeting.get('transcript_file')
    if not transcript_file:
        return PlainTextResponse("")
    
    # Try to find transcript file
    possible_paths = [
        ROOT / "data" / "mock_data_json" / "calendar" / "transcripts" / transcript_file,
        ROOT / "frontend" / "public" / "data" / "meetings" / "transcripts" / transcript_file,
    ]
    
    for path in possible_paths:
        if path.exists():
            try:
                return PlainTextResponse(path.read_text(encoding="utf-8"))
            except:
                continue
    
    return PlainTextResponse("")

@router.post('/meetings')
async def create_meeting(payload: dict):
    meetings = await repo_adapter.get_meetings()
    meetings.append(payload)
    await repo_adapter.save_meetings(meetings)
    return payload

@router.put('/meetings/{meeting_id}')
async def update_meeting(meeting_id: str, payload: dict):
    meetings = await repo_adapter.get_meetings()
    idx = next((i for i, x in enumerate(meetings) if x.get('meeting_id') == meeting_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail='Meeting not found')
    meetings[idx] = payload
    await repo_adapter.save_meetings(meetings)
    return meetings[idx]

@router.delete('/meetings/{meeting_id}')
async def delete_meeting(meeting_id: str):
    meetings = await repo_adapter.get_meetings()
    meetings = [m for m in meetings if m.get('meeting_id') != meeting_id]
    await repo_adapter.save_meetings(meetings)
    return {'status': 'deleted'}
