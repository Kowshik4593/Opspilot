from fastapi import APIRouter, HTTPException
from typing import List, Optional
from memory.vector_store import create_memory, MemoryType

router = APIRouter()

@router.post('/memory/{agent_name}/remember')
async def remember(agent_name: str, payload: dict):
    mem = create_memory(agent_name)
    content = payload.get('content')
    mtype = payload.get('memory_type')
    metadata = payload.get('metadata', {})
    if not content:
        raise HTTPException(status_code=400, detail='content required')
    mem_id = mem.remember(content, MemoryType(mtype) if mtype else None, metadata)
    return {'memory_id': mem_id}

@router.post('/memory/{agent_name}/recall')
async def recall(agent_name: str, payload: dict):
    mem = create_memory(agent_name)
    query = payload.get('query')
    n = int(payload.get('n', 5))
    if not query:
        raise HTTPException(status_code=400, detail='query required')
    return mem.recall(query, n_results=n)

@router.get('/memory/{agent_name}/recent')
async def recent(agent_name: str, n: Optional[int] = 10):
    mem = create_memory(agent_name)
    return mem.get_recent(n)

@router.delete('/memory/{agent_name}/{memory_id}')
async def forget(agent_name: str, memory_id: str):
    mem = create_memory(agent_name)
    mem.forget(memory_id)
    return {'status': 'deleted'}

@router.get('/memory/{agent_name}/export')
async def export(agent_name: str):
    mem = create_memory(agent_name)
    return mem.export()
