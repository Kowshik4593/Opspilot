
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict, Any
from config.settings import SETTINGS

USAGE_FILE = SETTINGS["data"]["governance"]["llm_usage"]

def _read_list(path: Path) -> list:
    if not path.exists(): return []
    try: return json.loads(path.read_text())
    except Exception: return []

def _write_list(path: Path, data: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))

def write_usage(agent: str, model: str, tokens_in: int, tokens_out: int,
                latency_ms: int, cost_usd: float, status: str,
                rate_limited: bool = False, retry_count: int = 0,
                correlation_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    entry = {
        "timestamp_utc": __import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat()+"+00:00",
        "agent": agent,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "cost_usd": round(cost_usd, 6),
        "status": status,
        "rate_limited": rate_limited,
        "retry_count": retry_count,
        "correlation_id": correlation_id,
        "meta": meta or {}
    }
    data = _read_list(USAGE_FILE)
    data.append(entry)
    _write_list(USAGE_FILE, data)
    return entry
