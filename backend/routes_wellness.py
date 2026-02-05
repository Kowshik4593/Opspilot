from fastapi import APIRouter, HTTPException
from backend import repo_adapter

router = APIRouter()

@router.get('/wellness')
async def get_wellness():
    return await repo_adapter.get_wellness()

@router.post('/wellness')
async def update_wellness(payload: dict):
    ok = await repo_adapter.save_wellness(payload)
    if not ok:
        raise HTTPException(status_code=500, detail='Unable to save wellness config')
    return payload
