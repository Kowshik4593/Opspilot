from typing import List, Any
from pathlib import Path
import json
from datetime import datetime
from backend.models import Email, Task, Followup
import anyio

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"  # we will read from workspace data/mock_data_json via relative path

# Helper to load json files (sync) and wrap for async
def _load_json(path: Path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

async def load_json_async(path: Path):
    return await anyio.to_thread.run_sync(_load_json, path)

async def get_emails() -> List[Email]:
    # prefer project data (where demo_sender writes), then frontend public data
    possible = [
        ROOT / "data" / "mock_data_json" / "emails" / "inbox.json",
        ROOT / "frontend" / "public" / "data" / "emails" / "inbox.json",
    ]
    for p in possible:
        if p.exists():
            raw = await load_json_async(p)
            emails = []
            for e in raw:
                # normalize dates
                if e.get("received_utc"):
                    try:
                        e["received_utc"] = e["received_utc"]
                    except:
                        pass
                emails.append(e)
            return emails
    return []

async def get_email(email_id: str) -> Any:
    emails = await get_emails()
    for e in emails:
        if e.get("email_id") == email_id:
            return e
    return None

async def get_tasks():
    possible = [
        ROOT / "data" / "mock_data_json" / "tasks" / "tasks.json",
        ROOT / "frontend" / "public" / "data" / "tasks" / "tasks.json",
    ]
    for p in possible:
        if p.exists():
            return await load_json_async(p)
    return []

async def save_tasks(tasks_data: list):
    # write to project data if writable
    possible = [
        ROOT / "data" / "mock_data_json" / "tasks" / "tasks.json",
    ]
    for p in possible:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(tasks_data, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            continue
    return False

async def save_followups(followups_data: list):
    possible = [
        ROOT / "data" / "mock_data_json" / "nudges" / "followups.json",
    ]
    for p in possible:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(followups_data, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            continue
    return False

async def get_followups():
    possible = [
        ROOT / "data" / "mock_data_json" / "nudges" / "followups.json",
        ROOT / "frontend" / "public" / "data" / "nudges" / "followups.json",
    ]
    for p in possible:
        if p.exists():
            return await load_json_async(p)
    return []

async def get_meetings():
    possible = [
        ROOT / "data" / "mock_data_json" / "calendar" / "meetings.json",
        ROOT / "frontend" / "public" / "data" / "meetings" / "meetings.json",
    ]
    for p in possible:
        if p.exists():
            return await load_json_async(p)
    return []

async def save_meetings(meetings_data: list):
    possible = [ROOT / "data" / "mock_data_json" / "calendar" / "meetings.json"]
    for p in possible:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(meetings_data, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            continue
    return False

async def get_wellness():
    possible = [
        ROOT / "data" / "mock_data_json" / "wellness" / "wellness_config.json",
        ROOT / "frontend" / "public" / "data" / "wellness" / "wellness_config.json",
    ]
    for p in possible:
        if p.exists():
            return await load_json_async(p)
    return {}

async def save_wellness(cfg: dict):
    possible = [ROOT / "data" / "mock_data_json" / "wellness" / "wellness_config.json"]
    for p in possible:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            continue
    return False

async def get_reports():
    possible = [
        ROOT / "data" / "mock_data_json" / "reporting" / "weekly.json",
        ROOT / "frontend" / "public" / "data" / "reporting" / "weekly.json",
    ]
    for p in possible:
        if p.exists():
            return await load_json_async(p)
    return []

async def save_reports(reports_data: list):
    possible = [ROOT / "data" / "mock_data_json" / "reporting" / "weekly.json"]
    for p in possible:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(reports_data, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            continue
    return False
