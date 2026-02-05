import anyio
import asyncio
from typing import Dict, Any
from backend.repo_adapter import get_email
from backend.events import push_event
from backend.embeddings import get_embedding

async def process_email_background(email_id: str):
    # Simple background processing: load email, emit start, provide a simple summary, emit complete
    await push_event({"event_type": "processing_started", "email_id": email_id, "content": f"Processing {email_id}"})

    # load email (repo_adapter.get_email expects event loop)
    email = await get_email(email_id)
    if not email:
        await push_event({"event_type": "error", "email_id": email_id, "content": "Email not found"})
        return

    # quick summary using first 300 chars
    body = email.get('body_text') or ''
    summary = body[:300]
    # Attempt to create an embedding (best-effort)
    try:
        emb = get_embedding(summary)
    except Exception:
        emb = None

    await push_event({"event_type": "summary", "email_id": email_id, "content": summary, "embedding_present": bool(emb)})

    # mark complete
    await push_event({"event_type": "processing_complete", "email_id": email_id, "content": "Processing completed"})

def schedule_email_processing(email_id: str):
    # convenience wrapper to schedule from sync contexts
    asyncio.create_task(process_email_background(email_id))
