# orchestration/autonomous_graph.py
"""
LangGraph Orchestration for Autonomous Email Processing
=======================================================
Implements a TRUE agentic workflow using LangGraph with:
- Conditional routing (agent decides next step)
- Loops (agent can iterate until done)
- Human-in-the-loop (approval gates)
- State persistence across steps

This is the core orchestration that makes the agent TRULY autonomous.
"""

from __future__ import annotations
from typing import TypedDict, Any, Dict, List, Literal, Optional, Annotated
from datetime import datetime, timedelta
import json
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Phase 1 imports - Memory & Enhanced Gateway
from memory import AgentMemory, MemoryType, EpisodicMemory, EpisodeType, EpisodeOutcome
from governance.litellm_gateway import EnhancedLiteLLMGateway

# Import our components
from agents.tools import TOOLS, ToolExecutor, get_approval_required_tools
from agents.schemas import AgentStatus, PendingAction


# ============================================================
# STATE DEFINITION
# ============================================================

class EmailProcessingState(TypedDict):
    """State for email processing workflow"""
    # Input
    email: Dict[str, Any]
    user_email: str
    
    # Processing state
    status: str  # idle, classifying, gathering_context, planning, executing, awaiting_approval, completed
    iteration: int
    max_iterations: int
    
    # Agent reasoning
    current_thought: str
    reasoning_trace: Annotated[List[Dict[str, Any]], operator.add]  # Append-only
    
    # Context gathered
    email_analysis: Optional[Dict[str, Any]]
    related_context: Dict[str, Any]
    
    # Phase 1: Memory context
    relevant_memories: List[Dict[str, Any]]
    past_similar_emails: List[Dict[str, Any]]
    episode_id: Optional[str]
    
    # Actions
    planned_actions: List[Dict[str, Any]]
    executed_actions: Annotated[List[str], operator.add]  # Append-only
    pending_approvals: List[Dict[str, Any]]
    
    # Output
    final_category: Optional[str]
    final_summary: Optional[str]
    
    # Tool execution
    current_tool: Optional[str]
    current_tool_params: Optional[Dict[str, Any]]
    tool_result: Optional[Dict[str, Any]]


# ============================================================
# NODE FUNCTIONS
# ============================================================

def recall_memory_context(state: EmailProcessingState) -> EmailProcessingState:
    """
    Pre-step: Recall memory context for email processing.
    Analyzes email content and recalls past patterns.
    """
    email = state["email"]
    user_email = state["user_email"]
    
    # Phase 1: Check memory for similar emails
    memory = AgentMemory("email_agent")
    episodic = EpisodicMemory("email_agent")
    
    relevant_memories = []
    past_similar_emails = []
    
    try:
        # Recall past interactions with this sender
        from_email = email.get("from_email", "")
        sender_memories = memory.recall(
            query=f"Past emails from {from_email} for user {user_email}",
            n_results=3,
            memory_type=MemoryType.INTERACTION
        )
        relevant_memories.extend(sender_memories)
        
        # Find similar past episodes
        similar_episodes = episodic.find_similar(
            episode_type=EpisodeType.EMAIL_PROCESSING,
            context_keys=["sender", "subject_keywords"],
            n_results=2
        )
        past_similar_emails = similar_episodes
        
    except Exception as e:
        # Non-critical, continue without memory
        pass
    
    return {
        **state,
        "relevant_memories": relevant_memories,
        "past_similar_emails": past_similar_emails
    }


def classify_email(state: EmailProcessingState) -> EmailProcessingState:
    """
    Node 1: Classify the incoming email
    Analyzes email content to determine type and urgency
    """
    email = state["email"]
    
    # Extract key signals
    subject = email.get("subject", "").lower()
    body = email.get("body_text", "").lower()
    from_email = email.get("from_email", "")
    
    # Determine urgency
    urgent_signals = ["urgent", "asap", "immediately", "critical", "blocker", "eod", "today"]
    is_urgent = any(signal in subject or signal in body for signal in urgent_signals)
    
    # Determine if external
    is_external = not from_email.endswith("@contoso.com")
    
    # Determine category
    pre_category = email.get("actionability_gt", "unknown")
    
    # Classify based on content
    if pre_category == "actionable" or is_urgent:
        category = "actionable"
        priority = "P0" if is_urgent else "P1"
    elif pre_category == "informational":
        category = "informational"
        priority = "P3"
    else:
        # Heuristic classification with expanded signals
        action_signals = [
            "can you", "could you", "please", "need", "require", "deadline", "by when", "review",
            "sync up", "sync-up", "perspective", "thoughts", "feedback", "discuss",
            "let me know", "get back to", "follow up", "following up", "waiting for",
            "action item", "next step", "schedule", "meeting", "call", "availability",
            "concerns", "issues", "blockers", "problems", "risks"
        ]
        # Check for bullet points or numbered lists (often indicate action items)
        has_list = any(marker in body for marker in ["- ", "* ", "1.", "2.", "+ "])
        has_action = any(signal in body for signal in action_signals) or has_list
        category = "actionable" if has_action else "informational"
        priority = "P2" if has_action else "P3"
    
    analysis = {
        "category": category,
        "priority": priority,
        "is_urgent": is_urgent,
        "is_external": is_external,
        "sender": from_email,
        "subject": email.get("subject", ""),
        "key_topics": _extract_topics(subject + " " + body),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    thought = f"""
Email Classification Complete
================================
Category: {category.upper()}
Priority: {priority}
Urgent: {'YES' if is_urgent else 'No'}
Sender: {from_email} ({'External' if is_external else 'Internal'})
Topics: {', '.join(analysis['key_topics'][:3])}

Next: {'Gathering context...' if category == 'actionable' else 'Minimal processing needed'}
"""
    
    return {
        **state,
        "status": "gathering_context" if category == "actionable" else "planning",
        "email_analysis": analysis,
        "current_thought": thought,
        "reasoning_trace": [{
            "step": "classify",
            "thought": thought,
            "result": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }],
        "iteration": state.get("iteration", 0) + 1
    }


def gather_context(state: EmailProcessingState) -> EmailProcessingState:
    """
    Node 2: Gather related context from emails, tasks, meetings
    The agent searches for information to make better decisions
    """
    email = state["email"]
    analysis = state.get("email_analysis", {})
    topics = analysis.get("key_topics", [])
    
    # Initialize tool executor (in real impl, this would be passed in)
    from repos.data_repo import DataRepo
    repo = DataRepo()
    executor = ToolExecutor(repo, None, state.get("user_email", "demo@awoa.local"))
    
    context = {"emails": [], "tasks": [], "meetings": []}
    
    # Search for related items using our tools
    for topic in topics[:2]:  # Limit to avoid too many searches
        # Search related emails
        email_result = executor.execute("search_emails", {
            "query": topic,
            "limit": 3
        })
        if email_result.get("success"):
            context["emails"].extend(email_result.get("result", {}).get("emails", []))
        
        # Search related tasks
        task_result = executor.execute("search_tasks", {
            "query": topic,
            "limit": 3
        })
        if task_result.get("success"):
            context["tasks"].extend(task_result.get("result", {}).get("tasks", []))
        
        # Search related meetings
        meeting_result = executor.execute("search_meetings", {
            "query": topic,
            "limit": 2
        })
        if meeting_result.get("success"):
            context["meetings"].extend(meeting_result.get("result", {}).get("meetings", []))
    
    # Deduplicate
    context["emails"] = _dedupe_by_key(context["emails"], "email_id")
    context["tasks"] = _dedupe_by_key(context["tasks"], "task_id")
    context["meetings"] = _dedupe_by_key(context["meetings"], "meeting_id")
    
    thought = f"""
Context Gathering Complete
================================
Found related items:
- Emails: {len(context['emails'])} related emails
- Tasks: {len(context['tasks'])} related tasks
- Meetings: {len(context['meetings'])} related meetings

Topics searched: {', '.join(topics[:2])}
Next: Planning actions based on context...
"""
    
    return {
        **state,
        "status": "planning",
        "related_context": context,
        "current_thought": thought,
        "reasoning_trace": [{
            "step": "gather_context",
            "thought": thought,
            "result": {
                "emails_found": len(context["emails"]),
                "tasks_found": len(context["tasks"]),
                "meetings_found": len(context["meetings"])
            },
            "timestamp": datetime.utcnow().isoformat()
        }]
    }


def plan_actions(state: EmailProcessingState) -> EmailProcessingState:
    """
    Node 3: Plan what actions to take based on email and context
    This is where the agent DECIDES what to do
    """
    email = state["email"]
    analysis = state.get("email_analysis", {})
    context = state.get("related_context", {})
    
    category = analysis.get("category", "informational")
    priority = analysis.get("priority", "P3")
    is_urgent = analysis.get("is_urgent", False)
    
    # Extract client/company from sender email
    from_email = email.get("from_email", "unknown@unknown.com")
    sender_name = email.get("sender_name", from_email.split("@")[0].replace(".", " ").title())
    domain = from_email.split("@")[-1].split(".")[0].title() if "@" in from_email else "Unknown"
    
    # Map known domains to client names
    client_map = {
        "Acmecorp": "Acme Corp",
        "Techvision": "TechVision",
        "Globaltech": "GlobalTech",
        "Contoso": "Internal"
    }
    client = client_map.get(domain, domain)
    
    planned_actions = []
    
    if category == "actionable":
        # Create a simple, clear task
        simple_subject = email.get('subject', 'Request')[:30]
        
        planned_actions.append({
            "action": "create_task",
            "params": {
                "title": f"Respond to {sender_name}" if len(simple_subject) > 25 else f"RE: {simple_subject}",
                "description": f"Email from: {sender_name} ({from_email})\nClient: {client}\nReceived: {email.get('received_utc', '')[:10]}\n\n---\nSubject: {email.get('subject', '')}\n\nAction needed: Review and respond to this email.\n\nEmail preview:\n{email.get('body_text', '')[:300]}...",
                "priority": priority,
                "source_type": "email",
                "source_ref_id": email.get("email_id"),
                "tags": [client.lower().replace(" ", "-"), "email-response", "agent-created"]
            },
            "requires_approval": False,
            "reason": f"Email from {client} ({priority}) - auto-created task"
        })
        
        # Plan: Draft reply - auto-generate without approval
        planned_actions.append({
            "action": "draft_email_reply",
            "params": {
                "email_id": email.get("email_id"),
                "tone": "urgent" if is_urgent else "professional",
                "key_points": [
                    "Acknowledge receipt",
                    "Confirm understanding of request",
                    "Provide timeline for response"
                ],
                "include_context": True
            },
            "requires_approval": False,
            "reason": f"Auto-drafted reply to {sender_name}"
        })
        
        # Create follow-up for actionable emails based on priority
        followup_days = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 2)
        followup_severity = {"P0": "critical", "P1": "high", "P2": "medium", "P3": "low"}.get(priority, "medium")
        followup_due = (datetime.utcnow() + timedelta(days=followup_days)).date().isoformat()
        
        planned_actions.append({
            "action": "create_followup",
            "params": {
                "entity_type": "email",
                "entity_id": email.get("email_id"),
                "reason": f"Follow up on {sender_name}'s request - {simple_subject}",
                "due_date": followup_due,
                "channel": "email",
                "severity": followup_severity
            },
            "requires_approval": False,
            "reason": f"Reminder to respond to {client} by {followup_due}"
        })
        
        # If related tasks exist, link them too
        if context.get("tasks"):
            existing_task = context["tasks"][0]
            planned_actions.append({
                "action": "create_followup",
                "params": {
                    "entity_type": "task",
                    "entity_id": existing_task.get("task_id"),
                    "reason": f"New email from {sender_name} about related topic",
                    "due_date": followup_due,
                    "channel": "email",
                    "severity": followup_severity
                },
                "requires_approval": False,
                "reason": f"Link to related task: {existing_task.get('title', 'Unknown')[:30]}"
            })
    
    else:
        # Even for informational emails, check if there are discussion points to track
        body = email.get("body_text", "").lower()
        has_discussion_points = any(marker in body for marker in ["- ", "* ", "1.", "2.", "+", "concerns", "areas", "points", "thoughts"])
        
        if has_discussion_points:
            # Create a low-priority task to review discussion points
            planned_actions.append({
                "action": "create_task",
                "params": {
                    "title": f"Review: {email.get('subject', 'Email')[:40]}",
                    "description": f"Email from: {sender_name} ({from_email})\nClient: {client}\nReceived: {email.get('received_utc', '')[:10]}\n\n---\nSubject: {email.get('subject', '')}\n\nContains discussion points to review.\n\nEmail preview:\n{email.get('body_text', '')[:300]}...",
                    "priority": "P3",
                    "source_type": "email",
                    "source_ref_id": email.get("email_id"),
                    "tags": [client.lower().replace(" ", "-"), "review", "agent-created"]
                },
                "requires_approval": False,
                "reason": f"Auto-created review task for {client} discussion"
            })
            
            # Also create a follow-up reminder
            follow_up_date = (datetime.utcnow() + timedelta(days=2)).date().isoformat()
            planned_actions.append({
                "action": "create_followup",
                "params": {
                    "entity_type": "email",
                    "entity_id": email.get("email_id"),
                    "reason": f"Reply to {sender_name} ({client}) - discussion points need review",
                    "due_date": follow_up_date,
                    "channel": "email",
                    "severity": "low"
                },
                "requires_approval": False,
                "reason": f"Reminder to respond to {sender_name} by {follow_up_date}"
            })
        
        # Always mark as processed
        planned_actions.append({
            "action": "mark_email_processed",
            "params": {
                "email_id": email.get("email_id"),
                "actions_taken": ["classified", "reviewed"] + (["task_created"] if has_discussion_points else []),
                "category": "informational"
            },
            "requires_approval": False,
            "reason": "Email processed"
        })
    
    actions_summary = "\n".join([f"  - {a['action']}: {a['reason']}" for a in planned_actions])
    
    thought = f"""
[*] Action Planning Complete
=====================================
Based on analysis, I will:
{actions_summary}

Total actions planned: {len(planned_actions)}
Requiring approval: {sum(1 for a in planned_actions if a.get('requires_approval'))}
Auto-executable: {sum(1 for a in planned_actions if not a.get('requires_approval'))}

Next: Executing actions...
"""
    
    return {
        **state,
        "status": "executing",
        "planned_actions": planned_actions,
        "current_thought": thought,
        "reasoning_trace": [{
            "step": "plan_actions",
            "thought": thought,
            "result": {"planned_count": len(planned_actions)},
            "timestamp": datetime.utcnow().isoformat()
        }]
    }


def execute_action(state: EmailProcessingState) -> EmailProcessingState:
    """
    Node 4: Execute the next planned action
    Actions requiring approval are queued, others are executed directly
    """
    planned_actions = state.get("planned_actions", [])
    pending_approvals = state.get("pending_approvals", [])
    
    if not planned_actions:
        return {
            **state,
            "status": "completed",
            "current_thought": "All actions processed.",
            "reasoning_trace": [{
                "step": "execute_complete",
                "thought": "No more actions to execute",
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    
    # Get next action
    action = planned_actions[0]
    remaining_actions = planned_actions[1:]
    
    action_name = action["action"]
    params = action["params"]
    requires_approval = action.get("requires_approval", False)
    
    # Initialize executor
    from repos.data_repo import DataRepo
    repo = DataRepo()
    executor = ToolExecutor(repo, None, state.get("user_email", "demo@awoa.local"))
    
    if requires_approval:
        # Queue for approval
        import uuid
        pending_action = {
            "action_id": f"pa_{uuid.uuid4().hex[:8]}",
            "action_type": action_name,
            "description": f"{action_name}: {action.get('reason', 'No reason')}",
            "payload": params,
            "reason": action.get("reason", ""),
            "source_email_id": state["email"].get("email_id"),
            "status": "pending",
            "created_utc": datetime.utcnow().isoformat()
        }
        pending_approvals.append(pending_action)
        
        thought = f"""
[PENDING] Action Queued for Approval
=====================================
Action: {action_name}
Reason: {action.get('reason', 'N/A')}

This action requires human approval before execution.
"""
        executed = f"{action_name} (queued for approval)"
    
    else:
        # Execute directly
        result = executor.execute(action_name, params)
        
        if result.get("success"):
            thought = f"""
[OK] Action Executed
=====================================
Action: {action_name}
Status: Success
"""
            executed = action_name
        else:
            thought = f"""
[FAIL] Action Failed
=====================================
Action: {action_name}
Error: {result.get('error', 'Unknown error')}
"""
            executed = f"{action_name} (failed)"
    
    return {
        **state,
        "status": "executing" if remaining_actions else "check_completion",
        "planned_actions": remaining_actions,
        "pending_approvals": pending_approvals,
        "current_thought": thought,
        "executed_actions": [executed],
        "reasoning_trace": [{
            "step": "execute_action",
            "action": action_name,
            "thought": thought,
            "requires_approval": requires_approval,
            "timestamp": datetime.utcnow().isoformat()
        }],
        "iteration": state.get("iteration", 0) + 1
    }


def check_completion(state: EmailProcessingState) -> EmailProcessingState:
    """
    Node 5: Check if processing is complete or needs more iterations
    """
    planned_actions = state.get("planned_actions", [])
    pending_approvals = state.get("pending_approvals", [])
    executed_actions = state.get("executed_actions", [])
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10)
    
    # Check if done
    if not planned_actions and iteration >= 2:
        status = "awaiting_approval" if pending_approvals else "completed"
        
        summary = f"""
[DONE] Processing Complete
=====================================
Email: {state['email'].get('subject', 'Unknown')[:40]}
Category: {state.get('email_analysis', {}).get('category', 'unknown')}

Actions Executed: {len(executed_actions)}
Pending Approvals: {len(pending_approvals)}

Status: {'Awaiting human approval' if pending_approvals else 'Complete'}
"""
        
        return {
            **state,
            "status": status,
            "final_summary": summary,
            "current_thought": summary,
            "reasoning_trace": [{
                "step": "completion_check",
                "thought": summary,
                "result": {
                    "executed": len(executed_actions),
                    "pending": len(pending_approvals),
                    "status": status
                },
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    
    # Safety check for max iterations
    if iteration >= max_iterations:
        return {
            **state,
            "status": "completed",
            "final_summary": f"Max iterations ({max_iterations}) reached. Stopping.",
            "reasoning_trace": [{
                "step": "max_iterations",
                "thought": "Safety limit reached",
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
    
    # Continue processing
    return {
        **state,
        "status": "executing",
        "reasoning_trace": [{
            "step": "continue",
            "thought": "Continuing to next action...",
            "timestamp": datetime.utcnow().isoformat()
        }]
    }


# ============================================================
# ROUTING FUNCTIONS (Conditional Edges)
# ============================================================

def route_after_classify(state: EmailProcessingState) -> Literal["gather_context", "plan_actions"]:
    """
    Decide whether to gather context or go straight to planning
    TRUE conditional routing - agent decides based on state
    """
    analysis = state.get("email_analysis", {})
    category = analysis.get("category", "informational")
    
    if category == "actionable":
        return "gather_context"  # Need more info for actionable emails
    else:
        return "plan_actions"  # Skip context for informational


def route_after_execute(state: EmailProcessingState) -> Literal["execute_action", "check_completion"]:
    """
    Decide whether to execute more actions or check completion
    This creates the LOOP - agent keeps executing until done
    """
    planned_actions = state.get("planned_actions", [])
    
    if planned_actions:
        return "execute_action"  # More actions to do
    else:
        return "check_completion"  # Check if we're done


def route_after_check(state: EmailProcessingState) -> Literal["plan_actions", "__end__"]:
    """
    Decide whether to replan or finish
    Allows agent to iterate if needed
    """
    status = state.get("status", "")
    iteration = state.get("iteration", 0)
    
    if status in ["completed", "awaiting_approval"]:
        return "__end__"
    elif iteration < state.get("max_iterations", 10):
        return "plan_actions"  # Replan if needed
    else:
        return "__end__"


# ============================================================
# GRAPH BUILDER
# ============================================================

def build_email_processing_graph():
    """
    Build the LangGraph workflow for autonomous email processing
    
    Graph structure:
    
    [START] -> classify -> route -> gather_context? -> plan_actions -> execute_action (loop) -> check_completion -> [END]
                              |                      /                             ^__________________|
                               plan_actions ---------
    """
    
    # Create the graph
    graph = StateGraph(EmailProcessingState)
    
    # Add nodes
    graph.add_node("classify", classify_email)
    graph.add_node("gather_context", gather_context)
    graph.add_node("plan_actions", plan_actions)
    graph.add_node("execute_action", execute_action)
    graph.add_node("check_completion", check_completion)
    
    # Set entry point
    graph.set_entry_point("classify")
    
    # Add conditional edges (THIS IS THE KEY TO AGENTIC BEHAVIOR)
    
    # After classify: decide if we need context
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "gather_context": "gather_context",
            "plan_actions": "plan_actions"
        }
    )
    
    # After gather_context: always go to planning
    graph.add_edge("gather_context", "plan_actions")
    
    # After planning: start executing
    graph.add_edge("plan_actions", "execute_action")
    
    # After execute: check if more actions OR check completion (LOOP)
    graph.add_conditional_edges(
        "execute_action",
        route_after_execute,
        {
            "execute_action": "execute_action",  # Loop back!
            "check_completion": "check_completion"
        }
    )
    
    # After check: maybe replan OR finish
    graph.add_conditional_edges(
        "check_completion",
        route_after_check,
        {
            "plan_actions": "plan_actions",  # Can go back to planning!
            "__end__": END
        }
    )
    
    # Compile with memory for checkpointing
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _extract_topics(text: str) -> List[str]:
    """Extract key topics/keywords from text"""
    # Simple keyword extraction
    keywords = []
    important_words = [
        "acme", "techvision", "globaltech", "api", "migration", "integration",
        "deadline", "urgent", "blocker", "review", "approval", "budget",
        "meeting", "call", "schedule", "timeline", "status", "update"
    ]
    
    text_lower = text.lower()
    for word in important_words:
        if word in text_lower:
            keywords.append(word)
    
    return keywords[:5]  # Limit


def _dedupe_by_key(items: List[Dict], key: str) -> List[Dict]:
    """Remove duplicates from list of dicts by key"""
    seen = set()
    result = []
    for item in items:
        k = item.get(key)
        if k and k not in seen:
            seen.add(k)
            result.append(item)
    return result


# ============================================================
# PUBLIC API
# ============================================================

def create_email_processor():
    """Create configured email processing graph"""
    return build_email_processing_graph()


def process_email_with_graph(email: Dict[str, Any], user_email: str = "kowshik.naidu@contoso.com"):
    """
    Process an email using the LangGraph workflow
    
    Returns a generator that yields state updates for real-time UI
    """
    graph = create_email_processor()
    
    initial_state: EmailProcessingState = {
        "email": email,
        "user_email": user_email,
        "status": "idle",
        "iteration": 0,
        "max_iterations": 10,
        "current_thought": "",
        "reasoning_trace": [],
        "email_analysis": None,
        "related_context": {},
        "planned_actions": [],
        "executed_actions": [],
        "pending_approvals": [],
        "final_category": None,
        "final_summary": None,
        "current_tool": None,
        "current_tool_params": None,
        "tool_result": None
    }
    
    config = {"configurable": {"thread_id": email.get("email_id", "default")}}
    
    # Stream the execution
    for event in graph.stream(initial_state, config):
        yield event
