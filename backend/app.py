import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends

from backend.routes_emails import router as emails_router
from backend.routes_agent import router as agent_router
from backend.routes_vector import router as vector_router
from backend.routes_events import router as events_router
from backend.routes_tasks import router as tasks_router
from backend.routes_meetings import router as meetings_router
from backend.routes_followups import router as followups_router
from backend.routes_wellness import router as wellness_router
from backend.routes_reports import router as reports_router
from backend.routes_memory import router as memory_router
from backend.routes_ai import router as ai_router
from backend.auth import get_api_key
from backend.env_validation import get_env_status

app = FastAPI(title="AWOA Backend API", version="0.1")

# Allow frontend origin (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(vector_router, prefix="/api/v1")
# Protect event, memory and agent control routes with API key
app.include_router(events_router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(meetings_router, prefix="/api/v1")
app.include_router(followups_router, prefix="/api/v1")
app.include_router(wellness_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(agent_router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(ai_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
