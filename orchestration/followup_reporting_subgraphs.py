# orchestration/followup_reporting_subgraphs.py
"""
Followup & Reporting Subgraphs - Lightweight Workflows
=====================================================
Two simple but effective subgraphs:

1. Followup Agent: Smart nudge generation for overdue items
2. Reporting Agent: Daily/weekly productivity summaries

Both integrate with Phase 1 memory for learning patterns.
"""

from __future__ import annotations
from typing import TypedDict, Any, Dict, List, Optional, Annotated
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Phase 1 imports
from memory import AgentMemory, MemoryType, EpisodicMemory, EpisodeOutcome
from governance.litellm_gateway import EnhancedLiteLLMGateway

# Agent imports
from agents.followup_agent import FollowupAgent
from agents.reporting_agent import ReportingAgent
from repos.data_repo import DataRepo


# ============================================================
# FOLLOWUP SUBGRAPH
# ============================================================

class FollowupState(TypedDict):
    """State for followup/nudge workflow"""
    user_email: str
    session_id: str
    status: str
    reasoning_trace: Annotated[List[str], operator.add]
    
    # Analysis
    overdue_items: List[Dict[str, Any]]
    nudges_generated: List[Dict[str, Any]]
    
    # Output
    result: Optional[Dict[str, Any]]


def scan_overdue_items(state: FollowupState) -> FollowupState:
    """Scan for overdue tasks/items needing followup"""
    repo = DataRepo()
    
    # Get all followups from data
    try:
        followups = repo.followups()
        state["overdue_items"] = followups
        state["reasoning_trace"].append(f"Found {len(followups)} items for followup")
    except:
        state["overdue_items"] = []
    
    state["status"] = "generating"
    return state


def generate_nudges(state: FollowupState) -> FollowupState:
    """Generate smart nudge messages"""
    repo = DataRepo()
    agent = FollowupAgent(repo)
    memory = AgentMemory("followup_agent")
    
    try:
        # Use existing agent logic
        nudges = agent.nudges()
        
        # Convert to dict format
        nudge_list = [
            {
                "followup_id": n.followup_id,
                "message": n.draft_message,
                "channel": n.recommended_channel,
                "severity": n.severity,
                "entity_type": n.entity_type
            }
            for n in nudges
        ]
        
        state["nudges_generated"] = nudge_list
        state["reasoning_trace"].append(f"Generated {len(nudge_list)} nudges")
        
        # Store successful pattern
        if nudge_list:
            memory.remember(
                content=f"Successfully generated {len(nudge_list)} followup nudges",
                memory_type=MemoryType.STRATEGY,
                metadata={"user": state["user_email"], "nudge_count": len(nudge_list)}
            )
        
    except Exception as e:
        state["nudges_generated"] = []
        state["reasoning_trace"].append(f"Error generating nudges: {str(e)}")
    
    state["status"] = "completed"
    state["result"] = {"nudges": state["nudges_generated"], "count": len(state["nudges_generated"])}
    
    return state


def create_followup_workflow() -> StateGraph:
    """Simple 2-node workflow for followup generation"""
    workflow = StateGraph(FollowupState)
    
    workflow.add_node("scan_overdue_items", scan_overdue_items)
    workflow.add_node("generate_nudges", generate_nudges)
    
    workflow.set_entry_point("scan_overdue_items")
    workflow.add_edge("scan_overdue_items", "generate_nudges")
    workflow.add_edge("generate_nudges", END)
    
    return workflow


def generate_followups(user_email: str) -> Dict[str, Any]:
    """Convenience function for followup generation"""
    graph = create_followup_workflow().compile()
    
    initial_state = {
        "user_email": user_email,
        "session_id": f"followup_{int(datetime.now().timestamp())}",
        "status": "idle",
        "reasoning_trace": [],
        "overdue_items": [],
        "nudges_generated": [],
        "result": None
    }
    
    result = graph.invoke(initial_state)
    return result.get("result", {})


# ============================================================
# REPORTING SUBGRAPH
# ============================================================

class ReportingState(TypedDict):
    """State for report generation workflow"""
    user_email: str
    report_type: str  # "eod", "weekly"
    session_id: str
    status: str
    reasoning_trace: Annotated[List[str], operator.add]
    
    # Data collection
    completed_tasks: List[Dict[str, Any]]
    attended_meetings: List[Dict[str, Any]]
    wellness_summary: Optional[Dict[str, Any]]
    
    # Analysis
    productivity_score: float
    key_achievements: List[str]
    
    # Output
    report: Optional[Dict[str, Any]]


def collect_report_data(state: ReportingState) -> ReportingState:
    """Collect data for report generation"""
    repo = DataRepo()
    user_email = state["user_email"]
    
    # Get completed tasks
    try:
        users = repo.users()
        user = next((u for u in users if u.get("email") == user_email), None)
        user_id = user["user_id"] if user else None
        
        tasks = repo.tasks()
        completed = [
            t for t in tasks
            if t.get("owner_user_id") == user_id
            and t.get("status") == "done"
        ]
        
        # Filter to today/this week based on report_type
        # For simplicity, take last 5 completed
        state["completed_tasks"] = completed[-5:]
        state["reasoning_trace"].append(f"Collected {len(state['completed_tasks'])} completed tasks")
        
    except:
        state["completed_tasks"] = []
    
    # Get meetings attended
    try:
        meetings = repo.meetings()
        attended = [
            m for m in meetings
            if user_email in m.get("attendees", [])
        ][-3:]  # Last 3 meetings
        
        state["attended_meetings"] = attended
        state["reasoning_trace"].append(f"Collected {len(attended)} meetings attended")
        
    except:
        state["attended_meetings"] = []
    
    state["status"] = "analyzing"
    return state


def analyze_productivity(state: ReportingState) -> ReportingState:
    """Analyze productivity metrics"""
    completed = state["completed_tasks"]
    meetings = state["attended_meetings"]
    
    # Simple productivity scoring
    score = 0
    score += len(completed) * 15  # Each completed task: 15 points
    score += len(meetings) * 5     # Each meeting: 5 points
    score = min(score, 100)
    
    state["productivity_score"] = score
    
    # Extract key achievements
    achievements = []
    for task in completed[:3]:  # Top 3
        if task.get("priority") in ["P0", "P1"]:
            achievements.append(f"Completed {task.get('priority')} task: {task.get('title', 'Untitled')}")
    
    state["key_achievements"] = achievements
    state["reasoning_trace"].append(f"Productivity score: {score:.0f}/100")
    
    state["status"] = "generating"
    return state


def generate_report(state: ReportingState) -> ReportingState:
    """Generate final report"""
    gateway = EnhancedLiteLLMGateway("reporting_agent", enable_cache=True)
    memory = AgentMemory("reporting_agent")
    
    report_type = state["report_type"]
    completed = state["completed_tasks"]
    meetings = state["attended_meetings"]
    score = state["productivity_score"]
    achievements = state["key_achievements"]
    
    # Build report structure
    report = {
        "type": report_type,
        "generated_at": datetime.now().isoformat(),
        "user_email": state["user_email"],
        "productivity_score": score,
        "summary": {
            "tasks_completed": len(completed),
            "meetings_attended": len(meetings),
            "key_achievements": achievements
        },
        "details": {
            "completed_tasks": [
                {"title": t.get("title"), "priority": t.get("priority")}
                for t in completed
            ],
            "meetings": [
                {"title": m.get("title"), "duration": m.get("duration_mins")}
                for m in meetings
            ]
        }
    }
    
    # Generate narrative summary with LLM
    try:
        prompt = f"""Generate a brief summary for this {report_type} report:

Completed Tasks: {len(completed)}
Key Achievements:
{chr(10).join(f'- {a}' for a in achievements)}

Meetings Attended: {len(meetings)}

Write 2-3 sentences highlighting the day's accomplishments."""

        narrative = gateway.call(
            prompt=prompt,
            temperature=0.5,
            use_cache=True,
            role_context="reporter"
        )
        
        report["narrative"] = narrative.strip()
        
    except:
        report["narrative"] = f"Completed {len(completed)} tasks and attended {len(meetings)} meetings today."
    
    state["report"] = report
    state["status"] = "completed"
    state["reasoning_trace"].append("Generated comprehensive report")
    
    # Store pattern
    try:
        memory.remember(
            content=f"Generated {report_type} report with {len(completed)} tasks",
            memory_type=MemoryType.INTERACTION,
            metadata={"user": state["user_email"], "report_type": report_type, "score": score}
        )
    except:
        pass
    
    return state


def create_reporting_workflow() -> StateGraph:
    """3-node workflow for report generation"""
    workflow = StateGraph(ReportingState)
    
    workflow.add_node("collect_report_data", collect_report_data)
    workflow.add_node("analyze_productivity", analyze_productivity)
    workflow.add_node("generate_report", generate_report)
    
    workflow.set_entry_point("collect_report_data")
    workflow.add_edge("collect_report_data", "analyze_productivity")
    workflow.add_edge("analyze_productivity", "generate_report")
    workflow.add_edge("generate_report", END)
    
    return workflow


def generate_report_for_user(user_email: str, report_type: str = "eod") -> Dict[str, Any]:
    """Convenience function for report generation"""
    graph = create_reporting_workflow().compile()
    
    initial_state = {
        "user_email": user_email,
        "report_type": report_type,
        "session_id": f"report_{int(datetime.now().timestamp())}",
        "status": "idle",
        "reasoning_trace": [],
        "completed_tasks": [],
        "attended_meetings": [],
        "wellness_summary": None,
        "productivity_score": 0.0,
        "key_achievements": [],
        "report": None
    }
    
    result = graph.invoke(initial_state)
    return result.get("report", {})


if __name__ == "__main__":
    print("Testing Followup Subgraph...")
    followup_result = generate_followups("kowshik.naidu@contoso.com")
    print(f"Generated {followup_result.get('count', 0)} nudges")
    
    print("\nTesting Reporting Subgraph...")
    report_result = generate_report_for_user("kowshik.naidu@contoso.com", "eod")
    print(f"Report score: {report_result.get('productivity_score', 0):.0f}/100")
    print(f"Tasks: {report_result.get('summary', {}).get('tasks_completed', 0)}")
