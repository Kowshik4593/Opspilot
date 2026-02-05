# orchestration/common_state.py
"""
Unified State Schema for Multi-Agent Coordination
==================================================
All workflows extend from WorkplaceState to enable:
- Cross-workflow context sharing
- Agent coordination
- Consistent state management
- Memory integration
"""

from __future__ import annotations
from typing import TypedDict, Annotated, Optional, List, Dict, Any
import operator


# ============================================================
# BASE STATE
# ============================================================

class WorkplaceState(TypedDict):
    """
    Base state shared across ALL agent workflows
    
    Design principles:
    - Append-only fields use Annotated[List, operator.add]
    - Shared context enables agent coordination
    - Memory integration for learning
    - Wellness monitoring built-in
    """
    
    # ===== Identity & Session =====
    user_email: str
    session_id: str
    workflow_type: str  # "email" | "meeting" | "task" | "wellness" | "chat" | "proactive"
    
    # ===== Current Focus =====
    current_entity_id: Optional[str]  # ID of email, task, meeting being processed
    current_entity_type: Optional[str]  # "email" | "task" | "meeting"
    current_entity_data: Dict[str, Any]  # Full entity data
    
    # ===== Shared Reasoning (Append-Only) =====
    # These accumulate across all workflow steps
    reasoning_trace: Annotated[List[Dict[str, Any]], operator.add]
    actions_taken: Annotated[List[str], operator.add]  # e.g., ["create_task:t123", "send_email:e456"]
    
    # ===== Cross-Workflow Context =====
    # Agents populate these to share context with other agents
    related_emails: List[Dict[str, Any]]  # Emails related to current work
    related_tasks: List[Dict[str, Any]]   # Tasks related to current work
    related_meetings: List[Dict[str, Any]]  # Meetings related to current work
    related_context: Dict[str, Any]  # Flexible context passing between agents
    
    # ===== Memory Integration =====
    relevant_memories: List[Dict[str, Any]]  # Retrieved from vector store
    episode_id: Optional[str]  # Current episodic memory episode
    
    # ===== Wellness & Workload Monitoring =====
    wellness_score: Optional[int]  # 0-100
    stress_level: Optional[str]  # "low" | "moderate" | "high" | "critical"
    burnout_signals: List[str]  # Warning signs detected
    workload_metrics: Dict[str, Any]  # P0 count, meeting hours, etc.
    
    # ===== Approval & Governance =====
    pending_approvals: List[Dict[str, Any]]  # Actions awaiting approval
    approval_required: bool  # True if workflow paused for approval
    approved_actions: Annotated[List[str], operator.add]  # Track approved actions
    rejected_actions: Annotated[List[str], operator.add]  # Track rejected actions
    
    # ===== Execution Metadata =====
    iteration: int  # Current iteration in workflow
    max_iterations: int  # Maximum iterations allowed
    status: str  # "idle" | "running" | "awaiting_approval" | "completed" | "error"
    error: Optional[str]  # Error message if status is "error"
    started_at: Optional[str]  # ISO timestamp
    completed_at: Optional[str]  # ISO timestamp
    
    # ===== Configuration =====
    user_preferences: Dict[str, Any]  # User-specific settings
    proactive_mode: bool  # True if triggered by proactive monitor


# ============================================================
# WORKFLOW-SPECIFIC STATE EXTENSIONS
# ============================================================

class EmailWorkflowState(WorkplaceState):
    """
    Email processing workflow state
    Extends base state with email-specific fields
    """
    # Email data
    email: Dict[str, Any]
    
    # Analysis results
    email_analysis: Optional[Dict[str, Any]]  # Category, urgency, topics
    extracted_actions: List[Dict[str, Any]]  # Action items from email
    
    # Planned actions
    planned_actions: List[Dict[str, Any]]  # Actions to execute
    
    # Generated outputs
    reply_draft: Optional[str]  # Draft response
    created_task_ids: Annotated[List[str], operator.add]  # Tasks created from email
    created_followup_ids: Annotated[List[str], operator.add]  # Follow-ups created
    
    # Classification
    final_category: Optional[str]  # "actionable" | "informational" | "noise"
    final_summary: Optional[str]  # Summary of email


class MeetingWorkflowState(WorkplaceState):
    """
    Meeting processing workflow state
    Extends base state with meeting-specific fields
    """
    # Meeting data
    meeting: Dict[str, Any]
    transcript: Optional[str]
    
    # Analysis results
    meeting_analysis: Optional[Dict[str, Any]]  # Topics, sentiment, etc.
    extracted_decisions: List[str]  # Decisions made in meeting
    extracted_action_items: List[Dict[str, Any]]  # Action items identified
    extracted_risks: List[str]  # Risks mentioned
    
    # Generated outputs
    mom: Optional[Dict[str, Any]]  # Minutes of Meeting
    created_tasks: Annotated[List[str], operator.add]  # Task IDs created
    notified_participants: Annotated[List[str], operator.add]  # Emails notified
    
    # Meeting metadata
    meeting_type: Optional[str]  # "standup" | "review" | "planning" | "retrospective"
    meeting_effectiveness: Optional[int]  # 1-10 score


class TaskWorkflowState(WorkplaceState):
    """
    Task planning/management workflow state
    Extends base state with task-specific fields
    """
    # Task data
    tasks: List[Dict[str, Any]]  # All user tasks
    
    # Analysis
    workload_analysis: Optional[Dict[str, Any]]  # Current workload breakdown
    priority_analysis: Dict[str, Any]  # Priority distribution
    
    # Planning outputs
    prioritized_tasks: List[Dict[str, Any]]  # Sorted by computed priority
    focus_blocks: List[Dict[str, Any]]  # Suggested time blocks
    plan_narrative: Optional[str]  # AI-generated plan description
    
    # Optimization
    bottlenecks: List[str]  # Identified blockers
    dependencies: List[Dict[str, Any]]  # Task dependencies
    suggested_delegations: List[Dict[str, Any]]  # Tasks to delegate


class WellnessWorkflowState(WorkplaceState):
    """
    Wellness monitoring workflow state
    Extends base state with wellness-specific fields
    """
    # Wellness data
    wellness_data: Optional[Dict[str, Any]]  # Full wellness assessment
    wellness_factors: List[Dict[str, Any]]  # Contributing factors
    
    # Intervention planning
    intervention_type: Optional[str]  # "break" | "nudge" | "alert" | "escalation"
    suggested_actions: List[str]  # Recommended interventions
    
    # Monitoring
    burnout_risk_level: Optional[str]  # "low" | "medium" | "high" | "critical"
    recent_mood_entries: List[Dict[str, Any]]  # Recent mood check-ins
    
    # Interventions executed
    break_suggested: bool
    nudge_sent: bool
    manager_alerted: bool


class ChatWorkflowState(WorkplaceState):
    """
    Conversational chat workflow state
    Extends base state with chat-specific fields
    """
    # Conversation
    user_query: str
    chat_history: List[Dict[str, str]]  # [{"role": "user"|"assistant", "content": "..."}]
    
    # Intent classification
    intent: Optional[str]  # Classified intent
    confidence: float  # Intent classification confidence (0.0-1.0)
    extracted_params: Dict[str, Any]  # Parameters extracted from query
    
    # Clarification
    clarification_needed: bool
    clarification_question: Optional[str]
    
    # Tool execution
    tool_calls: List[Dict[str, Any]]  # Tools to call
    tool_results: Dict[str, Any]  # Results from tools
    
    # Response generation
    final_response: Optional[str]
    response_sources: List[str]  # What data sources were used


class ProactiveWorkflowState(WorkplaceState):
    """
    Proactive monitoring workflow state
    Extends base state with proactive monitoring fields
    """
    # Alerts detected
    alerts: List[Dict[str, Any]]  # Detected issues
    alert_severity: str  # "low" | "medium" | "high" | "critical"
    
    # Analysis
    stalled_threads: List[Dict[str, Any]]  # Emails needing follow-up
    approaching_deadlines: List[Dict[str, Any]]  # Tasks due soon
    meeting_prep_needed: List[Dict[str, Any]]  # Meetings need preparation
    
    # Actions planned
    proactive_actions: List[Dict[str, Any]]  # Actions agent will take
    
    # User notification
    notify_user: bool
    notification_message: Optional[str]


# ============================================================
# STATE UTILITIES
# ============================================================

def create_initial_state(
    workflow_type: str,
    user_email: str,
    session_id: str,
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_data: Dict[str, Any] = None,
    max_iterations: int = 10
) -> WorkplaceState:
    """
    Factory function to create initial state for any workflow
    
    Args:
        workflow_type: Type of workflow to create state for
        user_email: User's email
        session_id: Unique session ID
        entity_id: ID of entity being processed (email, task, meeting)
        entity_type: Type of entity
        entity_data: Full entity data
        max_iterations: Maximum workflow iterations
    
    Returns:
        Initial state dict
    """
    from datetime import datetime
    
    return {
        # Identity
        "user_email": user_email,
        "session_id": session_id,
        "workflow_type": workflow_type,
        
        # Current focus
        "current_entity_id": entity_id,
        "current_entity_type": entity_type,
        "current_entity_data": entity_data or {},
        
        # Reasoning (empty lists)
        "reasoning_trace": [],
        "actions_taken": [],
        
        # Context (empty)
        "related_emails": [],
        "related_tasks": [],
        "related_meetings": [],
        "related_context": {},
        
        # Memory
        "relevant_memories": [],
        "episode_id": None,
        
        # Wellness
        "wellness_score": None,
        "stress_level": None,
        "burnout_signals": [],
        "workload_metrics": {},
        
        # Approval
        "pending_approvals": [],
        "approval_required": False,
        "approved_actions": [],
        "rejected_actions": [],
        
        # Execution
        "iteration": 0,
        "max_iterations": max_iterations,
        "status": "idle",
        "error": None,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        
        # Config
        "user_preferences": {},
        "proactive_mode": False
    }


def merge_state_updates(
    current_state: WorkplaceState,
    updates: Dict[str, Any]
) -> WorkplaceState:
    """
    Merge state updates, handling append-only fields correctly
    
    LangGraph automatically handles Annotated[List, operator.add] fields,
    but this is useful for manual state updates.
    """
    merged = {**current_state}
    
    # Append-only fields
    append_fields = [
        "reasoning_trace",
        "actions_taken",
        "approved_actions",
        "rejected_actions"
    ]
    
    for field in append_fields:
        if field in updates:
            # Append to existing list
            merged[field] = current_state.get(field, []) + updates[field]
    
    # Regular fields (last-write-wins)
    for key, value in updates.items():
        if key not in append_fields:
            merged[key] = value
    
    return merged


def extract_insights(state: WorkplaceState) -> Dict[str, Any]:
    """
    Extract insights from completed workflow state
    Useful for learning and analytics
    """
    return {
        "workflow_type": state["workflow_type"],
        "user_email": state["user_email"],
        "session_id": state["session_id"],
        "total_iterations": state["iteration"],
        "total_actions": len(state.get("actions_taken", [])),
        "status": state["status"],
        "wellness_score": state.get("wellness_score"),
        "stress_level": state.get("stress_level"),
        "approvals_needed": len(state.get("pending_approvals", [])),
        "approvals_approved": len(state.get("approved_actions", [])),
        "approvals_rejected": len(state.get("rejected_actions", [])),
        "cross_workflow_context": {
            "related_emails": len(state.get("related_emails", [])),
            "related_tasks": len(state.get("related_tasks", [])),
            "related_meetings": len(state.get("related_meetings", []))
        }
    }
