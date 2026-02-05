from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import Dict, Any, List
from backend.models import ProcessResponse, AgentEvent
import anyio
from backend import worker
from backend.auth import get_api_key

router = APIRouter()

# We'll try to use existing agent modules if available
try:
    from agents.autonomous_inbox import get_processor, get_processor_state, process_email_immediately
    AGENTS_AVAILABLE = True
except Exception:
    AGENTS_AVAILABLE = False

@router.get('/agent/status')
async def agent_status() -> Dict[str, Any]:
    if not AGENTS_AVAILABLE:
        return {"is_running": False, "info": "agents not available in this environment"}
    state = get_processor_state()
    return state

@router.post('/agent/start')
async def agent_start():
    if not AGENTS_AVAILABLE:
        raise HTTPException(status_code=500, detail='Agent modules not available')
    proc = get_processor()
    proc.start()
    return {"status": "started"}

@router.post('/agent/stop')
async def agent_stop():
    if not AGENTS_AVAILABLE:
        raise HTTPException(status_code=500, detail='Agent modules not available')
    proc = get_processor()
    proc.stop()
    return {"status": "stopped"}

@router.post('/agent/process-email')
async def process_email(payload: Dict[str, str], background_tasks: BackgroundTasks, api_key: str = Depends(get_api_key)):
    # payload: {"email_id": "..."}
    email_id = payload.get('email_id')
    if not email_id:
        raise HTTPException(status_code=400, detail='email_id required')
    # If native agents are available, they may still be used, but we schedule our generic worker
    # Schedule background processing (non-blocking)
    background_tasks.add_task(worker.schedule_email_processing, email_id)
    return ProcessResponse(task_id=email_id, status='processing', summary='Scheduled for background processing')

# Simple events polling endpoint (frontend can poll recent events)
@router.get('/agent/events', response_model=List[AgentEvent])
async def agent_events():
    if not AGENTS_AVAILABLE:
        return []
    proc_state = get_processor_state()
    events = proc_state.get('recent_events', [])
    # normalize
    out = []
    for i, e in enumerate(events[-50:]):
        d = e.to_dict() if hasattr(e, 'to_dict') else e
        out.append(AgentEvent(id=str(i), event_type=d.get('event_type','info'), content=d.get('content',''), timestamp=None, email_id=d.get('email_id')))
    return out
