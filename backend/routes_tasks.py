from fastapi import APIRouter, HTTPException
from backend import repo_adapter

router = APIRouter()

@router.get('/tasks')
async def list_tasks():
    tasks = await repo_adapter.get_tasks()
    return tasks

@router.get('/tasks/{task_id}')
async def get_task(task_id: str):
    tasks = await repo_adapter.get_tasks()
    t = next((x for x in tasks if x.get('task_id') == task_id), None)
    if not t:
        raise HTTPException(status_code=404, detail='Task not found')
    return t

@router.post('/tasks')
async def create_task(payload: dict):
    tasks = await repo_adapter.get_tasks()
    d = payload
    tasks.append(d)
    await repo_adapter.save_tasks(tasks)
    return d

@router.put('/tasks/{task_id}')
async def update_task(task_id: str, payload: dict):
    tasks = await repo_adapter.get_tasks()
    idx = next((i for i, x in enumerate(tasks) if x.get('task_id') == task_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail='Task not found')
    tasks[idx] = payload
    await repo_adapter.save_tasks(tasks)
    return tasks[idx]

@router.patch('/tasks/{task_id}')
async def patch_task(task_id: str, payload: dict):
    """Partial update - only updates provided fields"""
    tasks = await repo_adapter.get_tasks()
    idx = next((i for i, x in enumerate(tasks) if x.get('task_id') == task_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail='Task not found')
    # Merge payload into existing task
    tasks[idx].update(payload)
    await repo_adapter.save_tasks(tasks)
    return tasks[idx]

@router.delete('/tasks/{task_id}')
async def delete_task(task_id: str):
    tasks = await repo_adapter.get_tasks()
    tasks = [t for t in tasks if t.get('task_id') != task_id]
    await repo_adapter.save_tasks(tasks)
    return {'status': 'deleted'}
