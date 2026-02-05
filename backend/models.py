from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class EmailAIAnalysis(BaseModel):
    summary: Optional[str]
    key_points: Optional[List[str]]
    sentiment: Optional[str]
    urgency: Optional[str]
    suggested_actions: Optional[List[str]]

class EmailTriage(BaseModel):
    category: Optional[Literal['actionable','informational','noise','unprocessed']]
    priority: Optional[str]
    suggested_action: Optional[str]

class Email(BaseModel):
    email_id: str
    thread_id: Optional[str] = None
    from_email: str
    sender_name: Optional[str] = None
    to_emails: List[str]
    subject: str
    body_text: str
    received_utc: Optional[datetime] = None
    actionability_gt: Optional[Literal['actionable','informational','noise']] = None
    processed: Optional[bool] = False
    agent_actions: Optional[List[str]] = None
    processed_utc: Optional[datetime] = None
    agent_category: Optional[str] = None
    triage_result: Optional[EmailTriage] = None
    ai_analysis: Optional[EmailAIAnalysis] = None

class Task(BaseModel):
    task_id: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    source_ref_id: Optional[str] = None
    owner_user_id: Optional[str] = None
    priority: Optional[Literal['P0','P1','P2','P3']] = None
    status: Optional[str] = None
    due_date_utc: Optional[datetime] = None
    created_utc: Optional[datetime] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None

class Followup(BaseModel):
    followup_id: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    owner_user_id: Optional[str] = None
    reason: Optional[str] = None
    next_contact_due_utc: Optional[datetime] = None
    draft_message_gt: Optional[str] = None
    severity: Optional[Literal['critical','high','medium','low']] = None
    status: Optional[str] = None

class AgentEvent(BaseModel):
    id: str
    event_type: str
    content: str
    timestamp: Optional[datetime] = None
    email_id: Optional[str] = None

# minimal wellness model
class WellnessConfig(BaseModel):
    version: Optional[str]
    score: Optional[int] = None
    description: Optional[str] = None
    score_weights: Optional[Dict[str, float]] = None

# Generic response models
class ProcessResponse(BaseModel):
    task_id: Optional[str] = None
    status: str
    summary: Optional[str] = None
    events: Optional[List[AgentEvent]] = None
