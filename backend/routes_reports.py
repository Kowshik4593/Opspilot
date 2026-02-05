from fastapi import APIRouter, HTTPException
from backend import repo_adapter

router = APIRouter()

@router.get('/reports')
async def list_reports():
    return await repo_adapter.get_reports()

@router.post('/reports')
async def create_report(payload: dict):
    r = await repo_adapter.get_reports()
    r.append(payload)
    await repo_adapter.save_reports(r)
    return payload

@router.put('/reports/{report_index}')
async def update_report(report_index: int, payload: dict):
    r = await repo_adapter.get_reports()
    if report_index < 0 or report_index >= len(r):
        raise HTTPException(status_code=404, detail='Report not found')
    r[report_index] = payload
    await repo_adapter.save_reports(r)
    return r[report_index]

@router.delete('/reports/{report_index}')
async def delete_report(report_index: int):
    r = await repo_adapter.get_reports()
    if report_index < 0 or report_index >= len(r):
        raise HTTPException(status_code=404, detail='Report not found')
    r.pop(report_index)
    await repo_adapter.save_reports(r)
    return {'status': 'deleted'}
