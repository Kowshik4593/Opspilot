from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend import repo_adapter
from backend.models import Email
from pydantic import parse_obj_as

router = APIRouter()

@router.get('/emails', response_model=List[Email])
async def list_emails(category: Optional[str] = Query(None), limit: int = 200):
    all_emails = await repo_adapter.get_emails()
    if category:
        filtered = [e for e in all_emails if e.get('actionability_gt') == category]
    else:
        filtered = all_emails
    return parse_obj_as(List[Email], filtered[:limit])

@router.get('/emails/{email_id}', response_model=Email)
async def read_email(email_id: str):
    e = await repo_adapter.get_email(email_id)
    if not e:
        raise HTTPException(status_code=404, detail='Email not found')
    return parse_obj_as(Email, e)
