## Testing

Run backend tests (requires server running on port 8001):

```bash
cd backend
python test_api.py
```

## Docker

Build and run the backend in Docker:

```bash
cd backend
docker build -t awoa-backend .
docker run -p 8000:8000 --env-file ../.env awoa-backend
```

# AWOA Backend (FastAPI)

This backend exposes REST endpoints for the AWOA frontend. Features:

- Email, Tasks, Meetings, Followups, Wellness, Reports CRUD endpoints
- Memory API (episodic + vector memory) with ChromaDB fallback
- Vector embeddings upsert/search (uses Azure embeddings if configured)
- SSE event streaming for agent traces
- Lightweight API key protection for sensitive routes

Run locally (using the project's virtualenv):

```bash
cd backend
python -m pip install -r requirements.txt
# set BACKEND_API_KEY in .env for protected endpoints (optional in dev)
C:/Users/306589/Documents/T1/.venv/Scripts/python.exe -m uvicorn app:app --reload --port 8001
```

Endpoints under `/api/v1/` — see `routes_*.py` files for details.
# AWOA Backend (FastAPI)

This is a minimal FastAPI scaffold to expose the existing data and agent controls to the Next.js frontend.

Quick start (from project root, assuming Python venv is active):

```powershell
cd backend
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Endpoints:
- GET /health
- GET /api/v1/emails
- GET /api/v1/emails/{email_id}
- POST /api/v1/agent/process-email  (body {"email_id": "..."})
- POST /api/v1/agent/start
- POST /api/v1/agent/stop
- GET /api/v1/agent/status
- GET /api/v1/agent/events

Notes:
- The scaffold reads data from `frontend/public/data/...` if present, otherwise from `data/mock_data_json/...` in the repo.
- Agent endpoints call into the existing `agents` modules if available in this environment. If not found, some endpoints gracefully return fallback data.
