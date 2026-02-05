
from __future__ import annotations
import json, uuid, datetime as dt
from pathlib import Path
from typing import List, Optional
from config.settings import SETTINGS

AUDIT_FILE = SETTINGS["data"]["governance"]["audit_log"]

def _read_list(path: Path) -> list:
    if not path.exists(): return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []

def _write_list(path: Path, data: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))

def write_audit(actor: str, agent: str, action: str,
                input_refs: List[str], output_refs: List[str],
                status: str, correlation_id: Optional[str] = None,
                notes: Optional[str] = None):
    rec = {
        "audit_id": f"audit_{uuid.uuid4().hex[:8]}",
        "timestamp_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat()+"+00:00",
        "actor": actor,
        "agent": agent,
        "action": action,
        "input_refs": input_refs,
        "output_refs": output_refs,
        "status": status,
        "correlation_id": correlation_id,
        "notes": notes
    }
    data = _read_list(AUDIT_FILE)
    data.append(rec)
    _write_list(AUDIT_FILE, data)
    return rec
