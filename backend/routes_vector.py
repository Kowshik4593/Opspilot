from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from backend import embeddings

router = APIRouter()

class UpsertItem(BaseModel):
    id: str
    text: str
    metadata: dict = {}

@router.post('/vector/upsert')
async def vector_upsert(item: UpsertItem):
    embeddings.upsert_vector(item.id, item.text, item.metadata)
    return {"status": "ok", "id": item.id}

class QueryReq(BaseModel):
    query: str
    k: int = 5

@router.post('/vector/search')
async def vector_search(req: QueryReq):
    results = embeddings.search_vectors(req.query, req.k)
    return results
