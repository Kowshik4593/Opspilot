
from __future__ import annotations
import json
import uuid
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
from config.settings import SETTINGS

def _load_json(path: Path) -> Any:
    if not path.exists(): return [] if path.suffix == ".json" else None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to load {path}: {e}")

def _save_json(path: Path, data: Any) -> None:
    """Save data to JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

class DataRepo:
    def __init__(self):
        d = SETTINGS["data"]
        self.paths = {
            "users": d["users"],
            "inbox": d["emails"]["inbox"],
            "threads": d["emails"]["threads"],
            "tasks": d["tasks"],
            "meetings": d["calendar"]["meetings"],
            "mom": d["calendar"]["mom"],
            "transcripts_dir": d["calendar"]["transcripts_dir"],
            "followups": d["nudges"],
            "eod": d["reporting"]["eod"],
            "weekly": d["reporting"]["weekly"],
            "audit_log": d["governance"]["audit_log"],
            "llm_usage": d["governance"]["llm_usage"],
        }
        # Cache
        self._cache = {}

    def _get(self, key: str):
        if key in self._cache: return self._cache[key]
        path = self.paths[key]
        data = _load_json(path) if path.suffix == ".json" else path
        self._cache[key] = data
        return data

    # Users
    def users(self) -> List[Dict[str, Any]]:
        return self._get("users")

    def user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return next((u for u in self.users() if u.get("email") == email), None)

    # Emails
    def inbox(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        items = self._get("inbox")
        return self._apply_filters(items, filters or {})

    # Tasks
    def tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        items = self._get("tasks")
        return self._apply_filters(items, filters or {})

    # Meetings & Transcripts & MoM
    def meetings(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        items = self._get("meetings")
        return self._apply_filters(items, filters or {})

    def get_transcript(self, transcript_file: Optional[str]) -> str:
        if not transcript_file or not isinstance(transcript_file, str):
            return ""
        path = self.paths["transcripts_dir"] / transcript_file
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    def mom_entries(self) -> List[Dict[str, Any]]:
        mom = self._get("mom")
        return mom if isinstance(mom, list) else []

    # Followups & Reporting
    def followups(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self._apply_filters(self._get("followups"), filters or {})

    def eod(self) -> List[Dict[str, Any]]:
        return self._get("eod")

    def weekly(self) -> List[Dict[str, Any]]:
        return self._get("weekly")

    @staticmethod
    def _apply_filters(items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        def match(it):
            for k, v in filters.items():
                if v is None: continue
                if k not in it: return False
                if isinstance(v, (list, tuple, set)):
                    if it[k] not in v: return False
                else:
                    if it[k] != v: return False
            return True
        return [it for it in items if match(it)]

    # ============================================================
    # WRITE OPERATIONS (for Agentic AI)
    # ============================================================

    def invalidate_cache(self, key: Optional[str] = None) -> None:
        """Clear cache to force reload from disk"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    # --- Email Operations ---
    
    def add_email_to_inbox(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new email to inbox (for demo sender portal)"""
        emails = _load_json(self.paths["inbox"]) or []
        
        # Ensure required fields
        if "email_id" not in email:
            email["email_id"] = f"eml_{uuid.uuid4().hex[:12]}"
        if "received_utc" not in email:
            email["received_utc"] = datetime.utcnow().isoformat()
        if "processed" not in email:
            email["processed"] = False
        if "agent_actions" not in email:
            email["agent_actions"] = []
        
        emails.insert(0, email)  # Add to top
        _save_json(self.paths["inbox"], emails)
        self.invalidate_cache("inbox")
        return email

    def get_unprocessed_emails(self) -> List[Dict[str, Any]]:
        """Get emails that haven't been processed by agent yet"""
        self.invalidate_cache("inbox")  # Always fresh
        emails = self.inbox()
        return [e for e in emails if not e.get("processed", False)]

    def mark_email_processed(self, email_id: str, actions_taken: List[str], category: str) -> bool:
        """Mark an email as processed by the agent"""
        emails = _load_json(self.paths["inbox"]) or []
        
        for email in emails:
            if email.get("email_id") == email_id:
                email["processed"] = True
                email["processed_utc"] = datetime.utcnow().isoformat()
                email["agent_actions"] = actions_taken
                email["agent_category"] = category
                _save_json(self.paths["inbox"], emails)
                self.invalidate_cache("inbox")
                return True
        return False

    def update_email(self, email_id: str, updates: Dict[str, Any]) -> bool:
        """Update email fields"""
        emails = _load_json(self.paths["inbox"]) or []
        
        for email in emails:
            if email.get("email_id") == email_id:
                email.update(updates)
                email["updated_utc"] = datetime.utcnow().isoformat()
                _save_json(self.paths["inbox"], emails)
                self.invalidate_cache("inbox")
                return True
        return False

    # --- Task Operations ---
    
    def create_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task"""
        tasks = _load_json(self.paths["tasks"]) or []
        
        # Ensure required fields
        if "task_id" not in task:
            task["task_id"] = f"tsk_{uuid.uuid4().hex[:8]}"
        if "created_utc" not in task:
            task["created_utc"] = datetime.utcnow().isoformat()
        if "status" not in task:
            task["status"] = "todo"
        
        tasks.append(task)
        _save_json(self.paths["tasks"], tasks)
        self.invalidate_cache("tasks")
        return task

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing task"""
        tasks = _load_json(self.paths["tasks"]) or []
        
        for task in tasks:
            if task.get("task_id") == task_id:
                task.update(updates)
                task["updated_utc"] = datetime.utcnow().isoformat()
                _save_json(self.paths["tasks"], tasks)
                self.invalidate_cache("tasks")
                return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        tasks = _load_json(self.paths["tasks"]) or []
        original_len = len(tasks)
        tasks = [t for t in tasks if t.get("task_id") != task_id]
        
        if len(tasks) < original_len:
            _save_json(self.paths["tasks"], tasks)
            self.invalidate_cache("tasks")
            return True
        return False

    # --- Follow-up Operations ---
    
    def get_followups(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all follow-ups, optionally filtered by status"""
        followups = _load_json(self.paths["followups"]) or []
        if status:
            followups = [f for f in followups if f.get("status") == status]
        return followups
    
    def create_followup(self, followup: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new follow-up"""
        followups = _load_json(self.paths["followups"]) or []
        
        if "followup_id" not in followup:
            followup["followup_id"] = f"fu_{uuid.uuid4().hex[:8]}"
        if "created_utc" not in followup:
            followup["created_utc"] = datetime.utcnow().isoformat()
        if "status" not in followup:
            followup["status"] = "pending"
        
        followups.append(followup)
        _save_json(self.paths["followups"], followups)
        self.invalidate_cache("followups")
        return followup

    def update_followup(self, followup_id: str, updates: Dict[str, Any]) -> bool:
        """Update a follow-up"""
        followups = _load_json(self.paths["followups"]) or []
        
        for fu in followups:
            if fu.get("followup_id") == followup_id:
                fu.update(updates)
                fu["updated_utc"] = datetime.utcnow().isoformat()
                _save_json(self.paths["followups"], followups)
                self.invalidate_cache("followups")
                return True
        return False

    # --- Meeting Operations ---
    
    def create_meeting(self, meeting: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new meeting"""
        meetings = _load_json(self.paths["meetings"]) or []
        
        if "meeting_id" not in meeting:
            meeting["meeting_id"] = f"mtg_{uuid.uuid4().hex[:8]}"
        if "created_utc" not in meeting:
            meeting["created_utc"] = datetime.utcnow().isoformat()
        
        meetings.append(meeting)
        _save_json(self.paths["meetings"], meetings)
        self.invalidate_cache("meetings")
        return meeting

    # --- Draft Storage ---
    
    def save_draft(self, draft_type: str, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Save a draft (email reply, etc.) for review"""
        drafts_path = self.paths.get("drafts")
        if not drafts_path:
            # Create drafts path if not configured
            drafts_path = Path(SETTINGS["data"]["emails"]["inbox"]).parent / "drafts.json"
            self.paths["drafts"] = drafts_path
        
        drafts = _load_json(drafts_path) or []
        
        if "draft_id" not in draft:
            draft["draft_id"] = f"draft_{uuid.uuid4().hex[:8]}"
        draft["draft_type"] = draft_type
        draft["created_utc"] = datetime.utcnow().isoformat()
        draft["status"] = "pending_review"
        
        drafts.append(draft)
        _save_json(drafts_path, drafts)
        return draft

    def get_drafts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get drafts, optionally filtered by status"""
        drafts_path = self.paths.get("drafts")
        if not drafts_path:
            drafts_path = Path(SETTINGS["data"]["emails"]["inbox"]).parent / "drafts.json"
            self.paths["drafts"] = drafts_path
        
        drafts = _load_json(drafts_path) or []
        if status:
            drafts = [d for d in drafts if d.get("status") == status]
        return drafts

    def update_draft(self, draft_id: str, updates: Dict[str, Any]) -> bool:
        """Update a draft"""
        drafts_path = self.paths.get("drafts")
        if not drafts_path:
            return False
        
        drafts = _load_json(drafts_path) or []
        for draft in drafts:
            if draft.get("draft_id") == draft_id:
                draft.update(updates)
                draft["updated_utc"] = datetime.utcnow().isoformat()
                _save_json(drafts_path, drafts)
                return True
        return False

