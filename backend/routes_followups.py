from fastapi import APIRouter, HTTPException
from backend import repo_adapter

router = APIRouter()

@router.get('/followups')
async def list_followups():
    return await repo_adapter.get_followups()

@router.post('/followups')
async def create_followup(payload: dict):
    f = await repo_adapter.get_followups()
    f.append(payload)
    await repo_adapter.save_followups(f)
    return payload

@router.put('/followups/{followup_id}')
async def update_followup(followup_id: str, payload: dict):
    f = await repo_adapter.get_followups()
    idx = next((i for i, x in enumerate(f) if x.get('followup_id') == followup_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail='Followup not found')
    f[idx] = payload
    await repo_adapter.save_followups(f)
    return f[idx]

@router.delete('/followups/{followup_id}')
async def delete_followup(followup_id: str):
    f = await repo_adapter.get_followups()
    f = [x for x in f if x.get('followup_id') != followup_id]
    await repo_adapter.save_followups(f)
    return {'status': 'deleted'}
