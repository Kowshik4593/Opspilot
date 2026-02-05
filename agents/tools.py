# agents/tools.py
"""
Tool Registry for Agentic AI
============================
Defines all tools the agent can use with OpenAI-compatible function schemas.
Each tool has: name, description, parameters schema, requires_approval flag, and execute() method.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, date
import json
import uuid
from pydantic import BaseModel, Field


# ============================================================
# TOOL SCHEMA DEFINITIONS
# ============================================================

@dataclass
class ToolParameter:
    """Single parameter definition"""
    name: str
    type: str  # string, integer, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class Tool:
    """Tool definition with OpenAI-compatible schema"""
    name: str
    description: str
    parameters: List[ToolParameter]
    requires_approval: bool = False
    category: str = "general"  # read, write, search, communicate, analyze
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOLS: Dict[str, Tool] = {}


def register_tool(tool: Tool) -> Tool:
    """Register a tool in the global registry"""
    TOOLS[tool.name] = tool
    return tool


# --- READ TOOLS ---

register_tool(Tool(
    name="read_email",
    description="Read the full content of a specific email by ID. Use this to get complete email details including body, sender, subject.",
    parameters=[
        ToolParameter("email_id", "string", "The unique email ID (e.g., 'eml_xxx')")
    ],
    requires_approval=False,
    category="read"
))

register_tool(Tool(
    name="search_emails",
    description="Search emails by various criteria. Returns a list of matching emails with summaries.",
    parameters=[
        ToolParameter("query", "string", "Search keywords to find in subject or body", required=False),
        ToolParameter("sender", "string", "Filter by sender email or name", required=False),
        ToolParameter("actionability", "string", "Filter by actionability", required=False, enum=["actionable", "informational", "noise"]),
        ToolParameter("days_back", "integer", "Only search emails from last N days", required=False, default=7),
        ToolParameter("limit", "integer", "Maximum results to return", required=False, default=10)
    ],
    requires_approval=False,
    category="search"
))

register_tool(Tool(
    name="get_email_thread",
    description="Get all emails in a conversation thread. Useful for understanding full context of a discussion.",
    parameters=[
        ToolParameter("thread_id", "string", "The thread ID to retrieve")
    ],
    requires_approval=False,
    category="read"
))

register_tool(Tool(
    name="read_task",
    description="Read details of a specific task by ID.",
    parameters=[
        ToolParameter("task_id", "string", "The unique task ID (e.g., 'tsk_xxx')")
    ],
    requires_approval=False,
    category="read"
))

register_tool(Tool(
    name="search_tasks",
    description="Search tasks by various criteria like priority, status, project, or keywords.",
    parameters=[
        ToolParameter("query", "string", "Search keywords in task title or description", required=False),
        ToolParameter("priority", "string", "Filter by priority", required=False, enum=["P0", "P1", "P2", "P3"]),
        ToolParameter("status", "string", "Filter by status", required=False, enum=["todo", "in_progress", "completed", "blocked"]),
        ToolParameter("project", "string", "Filter by project/client (e.g., 'acme', 'techvision')", required=False),
        ToolParameter("due_filter", "string", "Filter by due date", required=False, enum=["overdue", "today", "this_week", "upcoming"]),
        ToolParameter("limit", "integer", "Maximum results", required=False, default=10)
    ],
    requires_approval=False,
    category="search"
))

register_tool(Tool(
    name="get_meeting",
    description="Get details of a specific meeting including participants, time, and transcript availability.",
    parameters=[
        ToolParameter("meeting_id", "string", "The unique meeting ID (e.g., 'mtg_xxx')")
    ],
    requires_approval=False,
    category="read"
))

register_tool(Tool(
    name="search_meetings",
    description="Search meetings by title, participants, or date range.",
    parameters=[
        ToolParameter("query", "string", "Search keywords in meeting title", required=False),
        ToolParameter("participant", "string", "Filter by participant email", required=False),
        ToolParameter("date_from", "string", "Start date (ISO format YYYY-MM-DD)", required=False),
        ToolParameter("date_to", "string", "End date (ISO format YYYY-MM-DD)", required=False),
        ToolParameter("limit", "integer", "Maximum results", required=False, default=5)
    ],
    requires_approval=False,
    category="search"
))

register_tool(Tool(
    name="get_meeting_transcript",
    description="Get the full transcript of a meeting. Use this to understand what was discussed.",
    parameters=[
        ToolParameter("meeting_id", "string", "The meeting ID to get transcript for")
    ],
    requires_approval=False,
    category="read"
))

register_tool(Tool(
    name="get_meeting_mom",
    description="Get the Minutes of Meeting (MoM) for a meeting, including decisions, action items, and risks.",
    parameters=[
        ToolParameter("meeting_id", "string", "The meeting ID to get MoM for")
    ],
    requires_approval=False,
    category="read"
))

register_tool(Tool(
    name="get_followups",
    description="Get pending follow-up items that need attention.",
    parameters=[
        ToolParameter("severity", "string", "Filter by severity", required=False, enum=["critical", "high", "medium", "low"]),
        ToolParameter("entity_type", "string", "Filter by type", required=False, enum=["task", "email", "meeting"]),
        ToolParameter("limit", "integer", "Maximum results", required=False, default=10)
    ],
    requires_approval=False,
    category="read"
))

register_tool(Tool(
    name="get_user_context",
    description="Get information about a user including their role, preferences, and communication style.",
    parameters=[
        ToolParameter("email", "string", "The user's email address")
    ],
    requires_approval=False,
    category="read"
))


# --- ANALYSIS TOOLS ---

register_tool(Tool(
    name="analyze_email",
    description="Use AI to analyze an email: categorize it, extract action items, identify urgency, and summarize content.",
    parameters=[
        ToolParameter("email_id", "string", "The email ID to analyze")
    ],
    requires_approval=False,
    category="analyze"
))

register_tool(Tool(
    name="generate_meeting_summary",
    description="Use AI to generate a comprehensive summary of a meeting from its transcript.",
    parameters=[
        ToolParameter("meeting_id", "string", "The meeting ID to summarize")
    ],
    requires_approval=False,
    category="analyze"
))

register_tool(Tool(
    name="analyze_priority",
    description="Analyze the priority and urgency of an email or task based on content, sender, and deadlines.",
    parameters=[
        ToolParameter("entity_type", "string", "Type of entity", enum=["email", "task"]),
        ToolParameter("entity_id", "string", "The ID of the email or task to analyze")
    ],
    requires_approval=False,
    category="analyze"
))

register_tool(Tool(
    name="find_related_context",
    description="Find related emails, tasks, and meetings for a given topic or entity. Useful for gathering context.",
    parameters=[
        ToolParameter("topic", "string", "The topic or keywords to find context for"),
        ToolParameter("entity_type", "string", "Optionally limit to entity type", required=False, enum=["email", "task", "meeting", "all"]),
        ToolParameter("limit", "integer", "Maximum results per type", required=False, default=5)
    ],
    requires_approval=False,
    category="search"
))


# --- WRITE TOOLS (Require Approval) ---

register_tool(Tool(
    name="create_task",
    description="Create a new task. Use this when an email or meeting requires follow-up action.",
    parameters=[
        ToolParameter("title", "string", "Task title (clear and actionable)"),
        ToolParameter("description", "string", "Detailed task description", required=False),
        ToolParameter("priority", "string", "Task priority", enum=["P0", "P1", "P2", "P3"]),
        ToolParameter("due_date", "string", "Due date in ISO format (YYYY-MM-DD)", required=False),
        ToolParameter("source_type", "string", "What created this task", enum=["email", "meeting", "manual", "agent"]),
        ToolParameter("source_ref_id", "string", "Reference ID of source (email_id or meeting_id)", required=False),
        ToolParameter("tags", "array", "Tags for categorization (e.g., ['acme', 'urgent'])", required=False)
    ],
    requires_approval=True,
    category="write"
))

register_tool(Tool(
    name="update_task",
    description="Update an existing task's status, priority, or other fields.",
    parameters=[
        ToolParameter("task_id", "string", "The task ID to update"),
        ToolParameter("status", "string", "New status", required=False, enum=["todo", "in_progress", "completed", "blocked"]),
        ToolParameter("priority", "string", "New priority", required=False, enum=["P0", "P1", "P2", "P3"]),
        ToolParameter("due_date", "string", "New due date (ISO format)", required=False),
        ToolParameter("notes", "string", "Add notes to task", required=False)
    ],
    requires_approval=True,
    category="write"
))

register_tool(Tool(
    name="draft_email_reply",
    description="Draft a reply to an email. The draft will be reviewed before sending.",
    parameters=[
        ToolParameter("email_id", "string", "The email ID to reply to"),
        ToolParameter("tone", "string", "Tone of the reply", enum=["professional", "friendly", "formal", "urgent"]),
        ToolParameter("key_points", "array", "Key points to include in the reply"),
        ToolParameter("include_context", "boolean", "Whether to include relevant context from meetings/tasks", required=False, default=True)
    ],
    requires_approval=True,
    category="communicate"
))

register_tool(Tool(
    name="send_email",
    description="Send an email (either a draft reply or new email). ALWAYS requires approval.",
    parameters=[
        ToolParameter("to_emails", "array", "List of recipient email addresses"),
        ToolParameter("subject", "string", "Email subject line"),
        ToolParameter("body", "string", "Email body content"),
        ToolParameter("reply_to_email_id", "string", "If replying, the original email ID", required=False),
        ToolParameter("cc_emails", "array", "CC recipients", required=False)
    ],
    requires_approval=True,
    category="communicate"
))

register_tool(Tool(
    name="create_followup",
    description="Create a follow-up reminder for a task or email.",
    parameters=[
        ToolParameter("entity_type", "string", "Type of entity to follow up on", enum=["task", "email", "meeting"]),
        ToolParameter("entity_id", "string", "ID of the entity"),
        ToolParameter("reason", "string", "Why follow-up is needed"),
        ToolParameter("due_date", "string", "When to follow up (ISO format)"),
        ToolParameter("channel", "string", "Recommended follow-up channel", enum=["email", "chat", "call"])
    ],
    requires_approval=True,
    category="write"
))

register_tool(Tool(
    name="schedule_meeting",
    description="Schedule a new meeting with participants.",
    parameters=[
        ToolParameter("title", "string", "Meeting title"),
        ToolParameter("description", "string", "Meeting description/agenda", required=False),
        ToolParameter("participants", "array", "List of participant emails"),
        ToolParameter("proposed_times", "array", "List of proposed time slots (ISO datetime strings)"),
        ToolParameter("duration_minutes", "integer", "Meeting duration in minutes", default=30)
    ],
    requires_approval=True,
    category="communicate"
))

register_tool(Tool(
    name="mark_email_processed",
    description="Mark an email as processed by the agent. Use this after completing all actions for an email.",
    parameters=[
        ToolParameter("email_id", "string", "The email ID to mark as processed"),
        ToolParameter("actions_taken", "array", "List of actions taken on this email"),
        ToolParameter("category", "string", "Final category assigned", enum=["actionable", "informational", "noise", "delegated"])
    ],
    requires_approval=False,  # Low risk - just marking status
    category="write"
))


# --- SPECIAL TOOLS ---

register_tool(Tool(
    name="think",
    description="Use this to record your thinking process. Helps with complex reasoning.",
    parameters=[
        ToolParameter("thought", "string", "Your reasoning or analysis")
    ],
    requires_approval=False,
    category="meta"
))

register_tool(Tool(
    name="finish",
    description="Signal that you have completed the task. Provide a summary of what was done.",
    parameters=[
        ToolParameter("summary", "string", "Summary of actions taken"),
        ToolParameter("actions_completed", "array", "List of completed actions"),
        ToolParameter("pending_approvals", "array", "List of actions waiting for approval", required=False)
    ],
    requires_approval=False,
    category="meta"
))

register_tool(Tool(
    name="request_human_input",
    description="Request clarification or input from the user when you're unsure how to proceed.",
    parameters=[
        ToolParameter("question", "string", "The question or clarification needed"),
        ToolParameter("options", "array", "Suggested options for the user to choose from", required=False),
        ToolParameter("context", "string", "Why you need this input", required=False)
    ],
    requires_approval=False,
    category="meta"
))


# ============================================================
# TOOL EXECUTION ENGINE
# ============================================================

class ToolExecutor:
    """Executes tools with the data repository and governance"""
    
    def __init__(self, repo, gateway=None, user_email: str = "demo@awoa.local"):
        self.repo = repo
        self.gateway = gateway
        self.user_email = user_email
        self._execution_log: List[Dict[str, Any]] = []
    
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result"""
        if tool_name not in TOOLS:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        tool = TOOLS[tool_name]
        
        # Log execution
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        self._execution_log.append({
            "execution_id": execution_id,
            "tool": tool_name,
            "parameters": parameters,
            "timestamp": datetime.utcnow().isoformat(),
            "requires_approval": tool.requires_approval
        })
        
        # Route to appropriate handler
        try:
            handler = getattr(self, f"_exec_{tool_name}", None)
            if handler:
                result = handler(parameters)
            else:
                result = {"success": False, "error": f"No handler for tool: {tool_name}"}
            
            return {
                "success": True,
                "execution_id": execution_id,
                "tool": tool_name,
                "requires_approval": tool.requires_approval,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "execution_id": execution_id,
                "tool": tool_name,
                "error": str(e)
            }
    
    # --- READ HANDLERS ---
    
    def _exec_read_email(self, params: Dict) -> Dict:
        email_id = params["email_id"]
        emails = self.repo.inbox()
        email = next((e for e in emails if e.get("email_id") == email_id), None)
        if not email:
            return {"found": False, "error": f"Email {email_id} not found"}
        return {"found": True, "email": email}
    
    def _exec_search_emails(self, params: Dict) -> Dict:
        emails = self.repo.inbox()
        results = []
        
        query = params.get("query", "").lower()
        sender = params.get("sender", "").lower()
        actionability = params.get("actionability")
        limit = params.get("limit", 10)
        
        for email in emails:
            # Apply filters
            if query and query not in email.get("subject", "").lower() and query not in email.get("body_text", "").lower():
                continue
            if sender and sender not in email.get("from_email", "").lower():
                continue
            if actionability and email.get("actionability_gt") != actionability:
                continue
            
            results.append({
                "email_id": email["email_id"],
                "subject": email["subject"],
                "from": email["from_email"],
                "received": email.get("received_utc", ""),
                "actionability": email.get("actionability_gt", "unknown"),
                "preview": email.get("body_text", "")[:150] + "..."
            })
            
            if len(results) >= limit:
                break
        
        return {"count": len(results), "emails": results}
    
    def _exec_search_tasks(self, params: Dict) -> Dict:
        tasks = self.repo.tasks()
        results = []
        
        query = params.get("query", "").lower()
        priority = params.get("priority")
        status = params.get("status")
        project = params.get("project", "").lower()
        limit = params.get("limit", 10)
        
        today = date.today().isoformat()
        
        for task in tasks:
            # Apply filters
            if query and query not in task.get("title", "").lower() and query not in (task.get("description") or "").lower():
                continue
            if priority and task.get("priority") != priority:
                continue
            if status and task.get("status") != status:
                continue
            if project and project not in " ".join(task.get("tags", [])).lower() and project not in task.get("title", "").lower():
                continue
            
            # Due filter
            due_filter = params.get("due_filter")
            if due_filter:
                due_date = (task.get("due_date_utc") or "9999")[:10]
                if due_filter == "overdue" and due_date >= today:
                    continue
                elif due_filter == "today" and due_date != today:
                    continue
            
            results.append({
                "task_id": task["task_id"],
                "title": task["title"],
                "priority": task.get("priority", "P3"),
                "status": task.get("status", "todo"),
                "due_date": task.get("due_date_utc", "")[:10] if task.get("due_date_utc") else None,
                "tags": task.get("tags", [])
            })
            
            if len(results) >= limit:
                break
        
        return {"count": len(results), "tasks": results}
    
    def _exec_search_meetings(self, params: Dict) -> Dict:
        meetings = self.repo.meetings()
        results = []
        
        query = params.get("query", "").lower()
        participant = params.get("participant", "").lower()
        limit = params.get("limit", 5)
        
        for mtg in meetings:
            if query and query not in mtg.get("title", "").lower():
                continue
            if participant:
                participants = [p.lower() for p in mtg.get("participant_emails", [])]
                if not any(participant in p for p in participants):
                    continue
            
            results.append({
                "meeting_id": mtg["meeting_id"],
                "title": mtg["title"],
                "scheduled_start": mtg.get("scheduled_start_utc", ""),
                "participants": mtg.get("participant_emails", []),
                "has_transcript": bool(mtg.get("transcript_file"))
            })
            
            if len(results) >= limit:
                break
        
        return {"count": len(results), "meetings": results}
    
    def _exec_get_meeting_transcript(self, params: Dict) -> Dict:
        meeting_id = params["meeting_id"]
        meetings = self.repo.meetings()
        mtg = next((m for m in meetings if m["meeting_id"] == meeting_id), None)
        
        if not mtg:
            return {"found": False, "error": f"Meeting {meeting_id} not found"}
        
        transcript_file = mtg.get("transcript_file")
        if not transcript_file:
            return {"found": True, "has_transcript": False, "transcript": None}
        
        transcript = self.repo.get_transcript(transcript_file)
        return {
            "found": True,
            "has_transcript": True,
            "meeting_title": mtg["title"],
            "transcript": transcript[:5000] if transcript else None  # Limit size
        }
    
    def _exec_get_meeting_mom(self, params: Dict) -> Dict:
        meeting_id = params["meeting_id"]
        mom_entries = self.repo.mom_entries()
        mom = next((m for m in mom_entries if m.get("meeting_id") == meeting_id), None)
        
        if not mom:
            return {"found": False, "meeting_id": meeting_id, "message": "No MoM found. Consider using generate_meeting_summary."}
        
        return {"found": True, "mom": mom}
    
    def _exec_get_followups(self, params: Dict) -> Dict:
        followups = self.repo.followups()
        results = []
        
        severity = params.get("severity")
        entity_type = params.get("entity_type")
        limit = params.get("limit", 10)
        
        for fu in followups:
            if severity and fu.get("severity") != severity:
                continue
            if entity_type and fu.get("entity_type") != entity_type:
                continue
            results.append(fu)
            if len(results) >= limit:
                break
        
        return {"count": len(results), "followups": results}
    
    def _exec_get_user_context(self, params: Dict) -> Dict:
        email = params["email"]
        user = self.repo.user_by_email(email)
        if not user:
            return {"found": False, "error": f"User {email} not found"}
        return {"found": True, "user": user}
    
    def _exec_find_related_context(self, params: Dict) -> Dict:
        topic = params.get("topic", "").lower()
        entity_type = params.get("entity_type", "all")
        limit = params.get("limit", 5)
        
        results = {"topic": topic, "related": {}}
        
        # Search emails
        if entity_type in ["all", "email"]:
            emails = self._exec_search_emails({"query": topic, "limit": limit})
            results["related"]["emails"] = emails.get("emails", [])
        
        # Search tasks
        if entity_type in ["all", "task"]:
            tasks = self._exec_search_tasks({"query": topic, "limit": limit})
            results["related"]["tasks"] = tasks.get("tasks", [])
        
        # Search meetings
        if entity_type in ["all", "meeting"]:
            meetings = self._exec_search_meetings({"query": topic, "limit": limit})
            results["related"]["meetings"] = meetings.get("meetings", [])
        
        return results
    
    # --- META HANDLERS ---
    
    def _exec_think(self, params: Dict) -> Dict:
        return {"recorded": True, "thought": params["thought"]}
    
    def _exec_finish(self, params: Dict) -> Dict:
        return {
            "completed": True,
            "summary": params["summary"],
            "actions_completed": params.get("actions_completed", []),
            "pending_approvals": params.get("pending_approvals", [])
        }
    
    def _exec_request_human_input(self, params: Dict) -> Dict:
        return {
            "awaiting_input": True,
            "question": params["question"],
            "options": params.get("options", []),
            "context": params.get("context", "")
        }
    
    # --- WRITE HANDLERS (Return pending action for approval) ---
    
    def _exec_create_task(self, params: Dict) -> Dict:
        # Lookup user_id from email
        user = self.repo.user_by_email(self.user_email)
        owner_user_id = user.get("user_id") if user else self.user_email
        
        # Build the task object
        task = {
            "task_id": f"tsk_{uuid.uuid4().hex[:8]}",
            "title": params["title"],
            "description": params.get("description", ""),
            "priority": params["priority"],
            "status": "todo",
            "due_date_utc": params.get("due_date"),
            "source": params.get("source_type", "email"),
            "source_ref_id": params.get("source_ref_id"),
            "owner_user_id": owner_user_id,
            "tags": params.get("tags", []),
            "created_utc": datetime.utcnow().isoformat(),
            "created_by": "agent"  # Mark as agent-created
        }
        
        # Agent is autonomous - always create task directly
        created_task = self.repo.create_task(task)
        return {"action": "create_task", "pending": False, "task": created_task, "success": True}
    
    def _exec_update_task(self, params: Dict) -> Dict:
        task_id = params["task_id"]
        updates = {k: v for k, v in params.items() if k != "task_id" and v is not None}
        
        # If updating to P0/P1 priority, require approval
        new_priority = updates.get("priority")
        if new_priority in ["P0", "P1"]:
            return {"action": "update_task", "pending": True, "task_id": task_id, "updates": updates, "requires_approval": True}
        else:
            # Non-critical update - apply directly
            success = self.repo.update_task(task_id, updates)
            return {"action": "update_task", "pending": False, "task_id": task_id, "success": success, "requires_approval": False}
    
    def _exec_draft_email_reply(self, params: Dict) -> Dict:
        email_id = params["email_id"]
        email_result = self._exec_read_email({"email_id": email_id})
        
        if not email_result.get("found"):
            return {"error": f"Email {email_id} not found"}
        
        email = email_result["email"]
        
        # In a real system, this would call the LLM to generate the draft
        draft = {
            "reply_to": email_id,
            "to_emails": [email["from_email"]],
            "subject": f"RE: {email['subject']}",
            "tone": params["tone"],
            "key_points": params.get("key_points", []),
            "include_context": params.get("include_context", True),
            "status": "draft"
        }
        return {"action": "draft_reply", "pending": True, "draft": draft, "original_email": email}
    
    def _exec_send_email(self, params: Dict) -> Dict:
        email = {
            "email_id": f"eml_out_{uuid.uuid4().hex[:8]}",
            "to_emails": params["to_emails"],
            "subject": params["subject"],
            "body": params["body"],
            "reply_to_email_id": params.get("reply_to_email_id"),
            "cc_emails": params.get("cc_emails", []),
            "status": "pending_send"
        }
        return {"action": "send_email", "pending": True, "email": email}
    
    def _exec_create_followup(self, params: Dict) -> Dict:
        followup = {
            "followup_id": f"fu_{uuid.uuid4().hex[:8]}",
            "entity_type": params["entity_type"],
            "entity_id": params["entity_id"],
            "reason": params.get("reason", "Agent created follow-up"),
            "due_date": params.get("due_date", datetime.utcnow().date().isoformat()),
            "severity": params.get("severity", "medium"),
            "channel": params.get("channel", "email"),
            "status": "pending",
            "created_by": "agent"
        }
        # Create directly (follow-ups don't need approval)
        created = self.repo.create_followup(followup)
        return {"action": "create_followup", "pending": False, "followup": created, "success": True}
    
    def _exec_mark_email_processed(self, params: Dict) -> Dict:
        return {
            "action": "mark_processed",
            "email_id": params["email_id"],
            "actions_taken": params.get("actions_taken", []),
            "category": params["category"]
        }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_all_tools() -> List[Tool]:
    """Get all registered tools"""
    return list(TOOLS.values())


def get_tools_by_category(category: str) -> List[Tool]:
    """Get tools filtered by category"""
    return [t for t in TOOLS.values() if t.category == category]


def get_tools_for_llm() -> List[Dict[str, Any]]:
    """Get all tools in OpenAI function calling format"""
    return [tool.to_openai_schema() for tool in TOOLS.values()]


def get_tool_names() -> List[str]:
    """Get list of all tool names"""
    return list(TOOLS.keys())


def get_approval_required_tools() -> List[str]:
    """Get tools that require human approval"""
    return [name for name, tool in TOOLS.items() if tool.requires_approval]
