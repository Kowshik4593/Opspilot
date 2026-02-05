# governance/approval.py
"""
Human-in-the-Loop Approval System
=================================
Manages pending actions that require human approval before execution.

Key features:
- Queue pending actions from agent
- Approve/Reject interface
- Execute approved actions
- Audit trail for all decisions
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json
import uuid

from config.settings import SETTINGS


# ============================================================
# PENDING ACTIONS STORAGE
# ============================================================

def _get_pending_actions_path() -> Path:
    """Get path to pending actions file"""
    governance_dir = Path(SETTINGS["data"]["governance"]["audit_log"]).parent
    return governance_dir / "pending_actions.json"


def _load_pending_actions() -> List[Dict[str, Any]]:
    """Load pending actions from file"""
    path = _get_pending_actions_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_pending_actions(actions: List[Dict[str, Any]]) -> None:
    """Save pending actions to file"""
    path = _get_pending_actions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(actions, indent=2, default=str), encoding="utf-8")


# ============================================================
# APPROVAL QUEUE MANAGEMENT
# ============================================================

class ApprovalQueue:
    """Manages the queue of actions awaiting human approval"""
    
    def __init__(self):
        self._cache: Optional[List[Dict[str, Any]]] = None
    
    def _load(self) -> List[Dict[str, Any]]:
        """Load with caching"""
        if self._cache is None:
            self._cache = _load_pending_actions()
        return self._cache
    
    def _save(self) -> None:
        """Save and invalidate cache"""
        if self._cache is not None:
            _save_pending_actions(self._cache)
    
    def invalidate_cache(self) -> None:
        """Force reload from disk"""
        self._cache = None
    
    def add_pending_action(
        self,
        action_type: str,
        payload: Dict[str, Any],
        reason: str,
        source_email_id: Optional[str] = None,
        source_meeting_id: Optional[str] = None,
        agent_reasoning: str = "",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a new action to the approval queue"""
        
        actions = self._load()
        
        action = {
            "action_id": f"pa_{uuid.uuid4().hex[:8]}",
            "action_type": action_type,
            "payload": payload,
            "reason": reason,
            "source_email_id": source_email_id,
            "source_meeting_id": source_meeting_id,
            "agent_reasoning": agent_reasoning,
            "session_id": session_id,
            "status": "pending",
            "created_utc": datetime.utcnow().isoformat(),
            "reviewed_utc": None,
            "reviewed_by": None,
            "execution_result": None
        }
        
        actions.append(action)
        self._cache = actions
        self._save()
        
        return action
    
    def get_pending_actions(self, status: str = "pending") -> List[Dict[str, Any]]:
        """Get actions filtered by status"""
        actions = self._load()
        return [a for a in actions if a.get("status") == status]
    
    def get_all_actions(self) -> List[Dict[str, Any]]:
        """Get all actions regardless of status"""
        return self._load()
    
    def get_action_by_id(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific action by ID"""
        actions = self._load()
        return next((a for a in actions if a.get("action_id") == action_id), None)
    
    def approve_action(
        self,
        action_id: str,
        reviewed_by: str = "user",
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Approve a pending action and execute it"""
        
        actions = self._load()
        
        for action in actions:
            if action.get("action_id") == action_id:
                if action.get("status") != "pending":
                    return None  # Already processed
                
                action["status"] = "approved"
                action["reviewed_utc"] = datetime.utcnow().isoformat()
                action["reviewed_by"] = reviewed_by
                action["review_notes"] = notes
                
                # Execute the action
                result = self._execute_action(action)
                action["execution_result"] = result
                action["status"] = "executed" if result.get("success") else "execution_failed"
                
                self._cache = actions
                self._save()
                
                # Log to audit
                self._log_approval(action, "approved")
                
                return action
        
        return None
    
    def reject_action(
        self,
        action_id: str,
        reviewed_by: str = "user",
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Reject a pending action"""
        
        actions = self._load()
        
        for action in actions:
            if action.get("action_id") == action_id:
                if action.get("status") != "pending":
                    return None  # Already processed
                
                action["status"] = "rejected"
                action["reviewed_utc"] = datetime.utcnow().isoformat()
                action["reviewed_by"] = reviewed_by
                action["rejection_reason"] = reason
                
                self._cache = actions
                self._save()
                
                # Log to audit
                self._log_approval(action, "rejected")
                
                return action
        
        return None
    
    def edit_and_approve(
        self,
        action_id: str,
        updated_payload: Dict[str, Any],
        reviewed_by: str = "user"
    ) -> Optional[Dict[str, Any]]:
        """Edit the payload and then approve"""
        
        actions = self._load()
        
        for action in actions:
            if action.get("action_id") == action_id:
                if action.get("status") != "pending":
                    return None
                
                action["original_payload"] = action["payload"]
                action["payload"] = updated_payload
                action["was_edited"] = True
                
                # Now approve
                self._cache = actions
                return self.approve_action(action_id, reviewed_by)
        
        return None
    
    def clear_old_actions(self, days: int = 7) -> int:
        """Remove actions older than specified days"""
        from datetime import timedelta
        
        actions = self._load()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        original_count = len(actions)
        actions = [
            a for a in actions
            if datetime.fromisoformat(a.get("created_utc", datetime.utcnow().isoformat())) > cutoff
            or a.get("status") == "pending"  # Keep pending actions
        ]
        
        self._cache = actions
        self._save()
        
        return original_count - len(actions)
    
    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an approved action"""
        from repos.data_repo import DataRepo
        
        repo = DataRepo()
        action_type = action.get("action_type")
        payload = action.get("payload", {})
        
        try:
            if action_type == "create_task":
                task = repo.create_task(payload)
                return {"success": True, "result": task}
            
            elif action_type == "update_task":
                task_id = payload.pop("task_id", None)
                if task_id:
                    success = repo.update_task(task_id, payload)
                    return {"success": success, "task_id": task_id}
                return {"success": False, "error": "No task_id provided"}
            
            elif action_type == "send_email":
                # In production, this would call an email API
                # For demo, we just log it
                return {
                    "success": True,
                    "result": "Email queued for sending",
                    "email": payload
                }
            
            elif action_type == "draft_email_reply":
                # Save as draft
                draft = repo.save_draft("email_reply", payload)
                return {"success": True, "result": draft}
            
            elif action_type == "create_followup":
                followup = repo.create_followup(payload)
                return {"success": True, "result": followup}
            
            elif action_type == "schedule_meeting":
                meeting = repo.create_meeting(payload)
                return {"success": True, "result": meeting}
            
            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _log_approval(self, action: Dict[str, Any], decision: str) -> None:
        """Log approval decision to audit"""
        try:
            from governance.audit import write_audit
            write_audit(
                actor=action.get("reviewed_by", "user"),
                agent="approval_system",
                action=f"action_{decision}",
                input_refs=[action.get("action_id")],
                output_refs=[action.get("action_type")],
                status="success",
                correlation_id=action.get("source_email_id")
            )
        except Exception:
            pass  # Don't fail if audit fails


# ============================================================
# APPROVAL POLICIES
# ============================================================

class ApprovalPolicy:
    """
    Defines which actions require approval and under what conditions.
    Can be extended for role-based approval workflows.
    """
    
    # Actions that ALWAYS require approval
    ALWAYS_REQUIRE = {
        "send_email",
        "schedule_meeting",
        "delete_task"
    }
    
    # Actions that require approval based on conditions
    CONDITIONAL_REQUIRE = {
        "create_task": lambda payload: payload.get("priority") in ["P0", "P1"],
        "update_task": lambda payload: "priority" in payload and payload["priority"] in ["P0", "P1"],
        "create_followup": lambda payload: True  # Always for now
    }
    
    # Actions that NEVER require approval (safe operations)
    NEVER_REQUIRE = {
        "read_email",
        "search_emails",
        "search_tasks",
        "search_meetings",
        "get_meeting_transcript",
        "get_meeting_mom",
        "find_related_context",
        "think",
        "mark_email_processed"
    }
    
    @classmethod
    def requires_approval(cls, action_type: str, payload: Dict[str, Any] = None) -> bool:
        """Check if an action requires approval"""
        
        if action_type in cls.NEVER_REQUIRE:
            return False
        
        if action_type in cls.ALWAYS_REQUIRE:
            return True
        
        if action_type in cls.CONDITIONAL_REQUIRE:
            checker = cls.CONDITIONAL_REQUIRE[action_type]
            return checker(payload or {})
        
        # Default: require approval for unknown actions
        return True


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

# Global queue instance
_approval_queue: Optional[ApprovalQueue] = None


def get_approval_queue() -> ApprovalQueue:
    """Get or create the global approval queue"""
    global _approval_queue
    if _approval_queue is None:
        _approval_queue = ApprovalQueue()
    return _approval_queue


def queue_action_for_approval(
    action_type: str,
    payload: Dict[str, Any],
    reason: str,
    source_email_id: Optional[str] = None,
    agent_reasoning: str = ""
) -> Dict[str, Any]:
    """Convenience function to queue an action"""
    queue = get_approval_queue()
    return queue.add_pending_action(
        action_type=action_type,
        payload=payload,
        reason=reason,
        source_email_id=source_email_id,
        agent_reasoning=agent_reasoning
    )


def get_pending_count() -> int:
    """Get count of pending approvals"""
    queue = get_approval_queue()
    return len(queue.get_pending_actions())


def approve_action(action_id: str, user: str = "user") -> Optional[Dict[str, Any]]:
    """Convenience function to approve an action"""
    queue = get_approval_queue()
    return queue.approve_action(action_id, reviewed_by=user)


def reject_action(action_id: str, user: str = "user", reason: str = "") -> Optional[Dict[str, Any]]:
    """Convenience function to reject an action"""
    queue = get_approval_queue()
    return queue.reject_action(action_id, reviewed_by=user, reason=reason)
