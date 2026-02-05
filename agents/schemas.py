
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ============================================================
# AGENTIC AI SCHEMAS
# ============================================================

class AgentStepType(str, Enum):
    """Type of step in agent reasoning"""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    FINISH = "finish"
    AWAIT_APPROVAL = "await_approval"
    AWAIT_INPUT = "await_input"
    ERROR = "error"


class AgentStatus(str, Enum):
    """Status of agent execution"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_INPUT = "awaiting_input"
    ERROR = "error"


class ToolCall(BaseModel):
    """Record of a tool call by the agent"""
    tool_name: str
    parameters: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    success: bool = True
    requires_approval: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentReasoningStep(BaseModel):
    """A single step in the agent's reasoning trace"""
    step_type: AgentStepType
    content: str
    tool_call: Optional[ToolCall] = None
    iteration: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PendingAction(BaseModel):
    """An action awaiting human approval"""
    action_id: str
    action_type: str  # create_task, send_email, etc.
    description: str
    payload: Dict[str, Any]
    reason: str
    source_email_id: Optional[str] = None
    source_meeting_id: Optional[str] = None
    agent_reasoning: str = ""
    status: str = "pending"  # pending, approved, rejected, executed
    created_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    reviewed_utc: Optional[str] = None
    reviewed_by: Optional[str] = None


class AgentSession(BaseModel):
    """A complete agent processing session"""
    session_id: str
    goal: str
    email_id: Optional[str] = None
    meeting_id: Optional[str] = None
    status: AgentStatus = AgentStatus.IDLE
    reasoning_trace: List[AgentReasoningStep] = []
    actions_taken: List[str] = []
    pending_approvals: List[PendingAction] = []
    context_gathered: Dict[str, Any] = {}
    final_summary: Optional[str] = None
    started_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_utc: Optional[str] = None
    total_iterations: int = 0


class AgentActivityEvent(BaseModel):
    """Real-time event from agent for UI updates"""
    event_id: str
    event_type: str  # new_email, thinking, action, observation, approval_needed, completed
    session_id: str
    content: str
    metadata: Dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================
# EMAIL AGENT SCHEMAS
# ============================================================

# Email Agent
class ExtractedAction(BaseModel):
    title: str
    owner_email: Optional[str]
    due_date_utc: Optional[str] = None  # ISO
    source_ref_id: Optional[str] = None

class EmailTriageResult(BaseModel):
    email_id: str
    triage_class: str = Field(..., description="actionable|informational|noise")
    summary: str
    actions: List[ExtractedAction] = []
    reply_draft: Optional[str] = None
    correlation_id: Optional[str] = None

# Tasks Agent
class TaskPlanBlock(BaseModel):
    title: str
    start_hint: Optional[str] = None
    duration_minutes: Optional[int] = 30

class TodayPlan(BaseModel):
    user_email: str
    narrative: str
    focus_blocks: List[TaskPlanBlock] = []

# Meeting Agent
class MoM(BaseModel):
    meeting_id: str
    summary: str
    decisions: List[str] = []
    action_items: List[str] = []
    risks: List[str] = []
    dependencies: List[str] = []
    correlation_id: Optional[str] = None
    delta_vs_existing: Optional[str] = None

# Follow-up Agent
class NudgeDraft(BaseModel):
    followup_id: str
    entity_type: str
    entity_id: str
    owner_user_id: str
    reason: str
    recommended_channel: str
    draft_message: str
    severity: str
    correlation_id: Optional[str] = None

# Reporting Agent
class Narrative(BaseModel):
    kind: str  # eod|weekly
    narrative: str
    correlation_ids: List[str] = []

# Wellness Agent
class WorkloadFactor(BaseModel):
    """Individual factor contributing to wellness score"""
    name: str = Field(..., description="Factor name: p0_tasks|overdue|meetings|focus_time|email_backlog|nudge_pressure")
    value: int = Field(..., description="Raw value (count or minutes)")
    impact: int = Field(..., description="Points deducted from wellness score")
    status: str = Field(..., description="green|yellow|orange|red")
    detail: str = Field(..., description="Human-readable detail")

class WellnessScore(BaseModel):
    """Overall wellness assessment"""
    score: int = Field(..., ge=0, le=100, description="Wellness score 0-100")
    level: str = Field(..., description="healthy|moderate|elevated|critical")
    factors: List[WorkloadFactor] = []
    summary: str = Field(..., description="Brief wellness summary")
    recommendations: List[str] = []
    timestamp: str = Field(..., description="ISO timestamp of assessment")

class BurnoutIndicator(BaseModel):
    """Burnout risk assessment"""
    risk_level: str = Field(..., description="low|medium|high|critical")
    signals: List[str] = []
    days_analyzed: int = 5
    recommendations: List[str] = []

class BreakSuggestion(BaseModel):
    """Break/recovery suggestion"""
    break_type: str = Field(..., description="micro|short|long")
    duration_minutes: int
    activity: str
    description: str
    emoji: str = "☕"

class FocusBlock(BaseModel):
    """Suggested focus/deep work block"""
    start_time: str
    end_time: str
    duration_minutes: int
    suggested_task: Optional[str] = None
    block_type: str = Field(default="deep_work", description="deep_work|pomodoro|buffer")

class MoodEntry(BaseModel):
    """Mood check-in entry"""
    mood: str = Field(..., description="great|okay|stressed|tired|overwhelmed")
    emoji: str
    timestamp: str
    notes: Optional[str] = None
    adjustments_made: List[str] = []

class WellnessNudge(BaseModel):
    """Proactive wellness notification"""
    nudge_id: str
    nudge_type: str = Field(..., description="break|workload|burnout|celebration|focus")
    severity: str = Field(..., description="info|warning|critical")
    title: str
    message: str
    suggested_action: Optional[str] = None
    correlation_id: Optional[str] = None

class MeetingDetoxSuggestion(BaseModel):
    """Meeting optimization suggestion"""
    meeting_id: str
    meeting_title: str
    suggestion_type: str = Field(..., description="decline|delegate|async|shorten|add_buffer")
    reason: str
    potential_time_saved_minutes: int
