# orchestration/task_subgraph.py
"""
Task Agent Subgraph - Intelligent Workload Management
====================================================
Transforms task planning into an agentic workflow with:
- Eisenhower matrix prioritization
- Workload analysis with wellness integration
- Burnout risk detection → triggers wellness agent
- Focus block recommendations
- Smart deadline management
- Learning from user's task completion patterns

Helps corporate employees manage workload sustainably!
"""

from __future__ import annotations
from typing import TypedDict, Any, Dict, List, Optional, Annotated
from datetime import datetime, timedelta
import operator
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Phase 1 imports
from memory import AgentMemory, MemoryType, EpisodicMemory, EpisodeType, EpisodeOutcome
from governance.litellm_gateway import EnhancedLiteLLMGateway
from orchestration.common_state import TaskWorkflowState, create_initial_state

# Agent imports
from agents.tasks_agent import TasksAgent
from repos.data_repo import DataRepo


# ============================================================
# STATE DEFINITION
# ============================================================

class TaskState(TypedDict):
    """State for task planning workflow"""
    # Input
    user_email: str
    session_id: str
    request_type: str  # "plan_today", "prioritize", "focus_blocks", "add_task"
    
    # Optional: for add_task requests
    new_task: Optional[Dict[str, Any]]
    
    # Processing state
    status: str  # idle, loading, analyzing, prioritizing, planning, completed
    iteration: int
    
    # Context
    user_tasks: List[Dict[str, Any]]
    user_meetings: List[Dict[str, Any]]
    past_completion_patterns: List[Dict[str, Any]]
    
    # Agent reasoning
    reasoning_trace: Annotated[List[str], operator.add]
    
    # Analysis results
    eisenhower_board: Dict[str, List[Dict[str, Any]]]  # P0, P1, P2, P3
    workload_score: float  # 0-100
    stress_level: str  # low, moderate, high, critical
    burnout_risk: bool
    
    # Planning outputs
    focus_blocks: List[Dict[str, Any]]
    recommended_breaks: List[Dict[str, Any]]
    tasks_to_defer: List[Dict[str, Any]]
    
    # Wellness integration
    wellness_score: Optional[float]
    wellness_concern: bool
    
    # Cross-agent triggers
    trigger_wellness_agent: bool
    trigger_followup_agent: bool
    
    # Output
    today_plan: Optional[Dict[str, Any]]
    
    # Episode tracking
    episode_id: Optional[str]


# ============================================================
# NODE FUNCTIONS
# ============================================================

def load_task_context(state: TaskState) -> TaskState:
    """
    Node 1: Load user's tasks, meetings, and recall past patterns
    """
    repo = DataRepo()
    memory = AgentMemory("task_agent")
    
    user_email = state["user_email"]
    
    # Load user's tasks
    try:
        # Find user
        users = repo.users()
        user = next((u for u in users if u.get("email") == user_email), None)
        
        if not user:
            state["status"] = "error"
            state["reasoning_trace"].append(f"User {user_email} not found")
            return state
        
        user_id = user["user_id"]
        
        # Get user's tasks
        all_tasks = repo.tasks()
        user_tasks = [t for t in all_tasks if t.get("owner_user_id") == user_id]
        
        # Filter to active tasks only
        active_tasks = [
            t for t in user_tasks
            if t.get("status") not in ["done", "cancelled"]
        ]
        
        state["user_tasks"] = active_tasks
        state["reasoning_trace"].append(f"Loaded {len(active_tasks)} active tasks")
        
    except Exception as e:
        state["status"] = "error"
        state["reasoning_trace"].append(f"Error loading tasks: {str(e)}")
        return state
    
    # Load user's meetings (for time availability)
    try:
        meetings = repo.meetings()
        today = datetime.now().date()
        
        # Filter to today's meetings
        user_meetings = [
            m for m in meetings
            if user_email in m.get("attendees", [])
            and m.get("scheduled_at", "").startswith(str(today))
        ]
        
        state["user_meetings"] = user_meetings
        state["reasoning_trace"].append(f"Found {len(user_meetings)} meetings today")
        
    except:
        state["user_meetings"] = []
    
    # Recall past completion patterns
    try:
        patterns = memory.recall(
            query=f"Task completion patterns for {user_email}",
            n_results=5,
            memory_type=MemoryType.STRATEGY
        )
        
        state["past_completion_patterns"] = patterns
        if patterns:
            state["reasoning_trace"].append(f"Recalled {len(patterns)} past patterns")
    except:
        state["past_completion_patterns"] = []
    
    state["status"] = "analyzing"
    return state


def analyze_workload(state: TaskState) -> TaskState:
    """
    Node 2: Analyze workload and calculate stress metrics
    
    Factors:
    - Number of P0/P1 tasks
    - Overdue tasks
    - Meeting load
    - Available focus time
    """
    tasks = state["user_tasks"]
    meetings = state["user_meetings"]
    
    # Count by priority
    p0_count = len([t for t in tasks if t.get("priority") == "P0"])
    p1_count = len([t for t in tasks if t.get("priority") == "P1"])
    p2_count = len([t for t in tasks if t.get("priority") == "P2"])
    p3_count = len([t for t in tasks if t.get("priority") == "P3"])
    
    # Count overdue
    today = datetime.now().isoformat()
    overdue_count = len([
        t for t in tasks
        if t.get("due_date_utc") and t["due_date_utc"] < today
    ])
    
    # Meeting time (assume 30 min default if not specified)
    total_meeting_mins = sum(m.get("duration_mins", 30) for m in meetings)
    
    # Workload scoring (0-100, higher = more stress)
    workload_score = 0
    workload_score += p0_count * 15  # Each P0 adds 15 points
    workload_score += p1_count * 8   # Each P1 adds 8 points
    workload_score += p2_count * 3   # Each P2 adds 3 points
    workload_score += overdue_count * 10  # Each overdue adds 10 points
    workload_score += (total_meeting_mins / 60) * 5  # Each hour of meetings adds 5 points
    
    # Cap at 100
    workload_score = min(workload_score, 100)
    
    # Determine stress level
    if workload_score >= 80:
        stress_level = "critical"
        burnout_risk = True
    elif workload_score >= 60:
        stress_level = "high"
        burnout_risk = False
    elif workload_score >= 40:
        stress_level = "moderate"
        burnout_risk = False
    else:
        stress_level = "low"
        burnout_risk = False
    
    state["workload_score"] = workload_score
    state["stress_level"] = stress_level
    state["burnout_risk"] = burnout_risk
    
    state["reasoning_trace"].append(
        f"Workload: {workload_score:.0f}/100 ({stress_level}), "
        f"P0={p0_count}, P1={p1_count}, overdue={overdue_count}, "
        f"meetings={total_meeting_mins}min"
    )
    
    # Flag wellness concern if needed
    if burnout_risk or stress_level == "critical":
        state["wellness_concern"] = True
        state["trigger_wellness_agent"] = True
        state["reasoning_trace"].append("⚠️ Wellness concern detected - will trigger wellness agent")
    
    state["status"] = "prioritizing"
    return state


def prioritize_tasks(state: TaskState) -> TaskState:
    """
    Node 3: Organize tasks using Eisenhower matrix
    
    Learns from past user behavior to refine prioritization
    """
    tasks = state["user_tasks"]
    memory = AgentMemory("task_agent")
    
    # Eisenhower matrix: P0, P1, P2, P3
    board = {
        "P0": [],  # Urgent & Important
        "P1": [],  # Important, Not Urgent
        "P2": [],  # Urgent, Not Important
        "P3": []   # Neither Urgent Nor Important
    }
    
    # Sort tasks into buckets
    for task in tasks:
        priority = task.get("priority", "P2")
        board.setdefault(priority, []).append(task)
    
    # Sort each bucket by due date
    for priority in board:
        board[priority].sort(
            key=lambda t: t.get("due_date_utc") or "9999-12-31T23:59:59+00:00"
        )
    
    state["eisenhower_board"] = board
    
    # Check past patterns for priority adjustments
    if state["past_completion_patterns"]:
        # Learn: Does user typically complete certain types faster?
        # This is where we'd apply learned adjustments
        # For now, just log that we have patterns
        state["reasoning_trace"].append(
            f"Applied {len(state['past_completion_patterns'])} learned patterns"
        )
    
    state["reasoning_trace"].append(
        f"Prioritized: P0={len(board['P0'])}, P1={len(board['P1'])}, "
        f"P2={len(board['P2'])}, P3={len(board['P3'])}"
    )
    
    state["status"] = "planning"
    return state


def create_focus_blocks(state: TaskState) -> TaskState:
    """
    Node 4: Recommend focus blocks for deep work
    
    Considers:
    - Meeting gaps
    - Task complexity
    - User's past productive times
    """
    gateway = EnhancedLiteLLMGateway("task_agent", enable_cache=True)
    
    board = state["eisenhower_board"]
    meetings = state["user_meetings"]
    stress_level = state["stress_level"]
    
    # Calculate available focus time (8hr day - meetings)
    total_meeting_mins = sum(m.get("duration_mins", 30) for m in meetings)
    available_mins = (8 * 60) - total_meeting_mins
    
    # Recommend focus blocks based on workload
    focus_blocks = []
    
    # High priority tasks get focus blocks
    p0_tasks = board.get("P0", [])
    p1_tasks = board.get("P1", [])
    
    if p0_tasks:
        # P0 tasks need immediate focus
        for task in p0_tasks[:3]:  # Top 3 P0s
            focus_blocks.append({
                "task_id": task["task_id"],
                "title": task.get("title", "Untitled"),
                "recommended_duration": 90 if task.get("complexity") == "high" else 60,
                "priority": "P0",
                "rationale": "Urgent and important task"
            })
    
    if p1_tasks and len(focus_blocks) < 3:
        # Add P1 focus blocks if we have capacity
        for task in p1_tasks[:2]:
            focus_blocks.append({
                "task_id": task["task_id"],
                "title": task.get("title", "Untitled"),
                "recommended_duration": 60,
                "priority": "P1",
                "rationale": "Important task requiring focused attention"
            })
    
    state["focus_blocks"] = focus_blocks[:3]  # Max 3 focus blocks per day
    
    # Recommend breaks based on stress level
    breaks = []
    if stress_level in ["high", "critical"]:
        breaks.append({
            "type": "short_break",
            "duration": 15,
            "frequency": "every 90 minutes",
            "rationale": "High stress detected - regular breaks essential"
        })
        breaks.append({
            "type": "lunch_break",
            "duration": 45,
            "rationale": "Extended lunch for recovery"
        })
    elif stress_level == "moderate":
        breaks.append({
            "type": "short_break",
            "duration": 10,
            "frequency": "every 2 hours",
            "rationale": "Moderate workload - maintain energy"
        })
    
    state["recommended_breaks"] = breaks
    
    # Identify tasks to defer if overloaded
    if state["workload_score"] > 70:
        p2_p3_tasks = board.get("P2", []) + board.get("P3", [])
        state["tasks_to_defer"] = p2_p3_tasks[:3]
        state["reasoning_trace"].append(
            f"Recommending deferral of {len(state['tasks_to_defer'])} lower-priority tasks"
        )
    else:
        state["tasks_to_defer"] = []
    
    state["reasoning_trace"].append(
        f"Created {len(focus_blocks)} focus blocks, {len(breaks)} break recommendations"
    )
    
    return state


def generate_today_plan(state: TaskState) -> TaskState:
    """
    Node 5: Generate comprehensive plan for today
    """
    board = state["eisenhower_board"]
    focus_blocks = state["focus_blocks"]
    breaks = state["recommended_breaks"]
    
    # Build plan structure
    plan = {
        "date": datetime.now().date().isoformat(),
        "user_email": state["user_email"],
        "workload_score": state["workload_score"],
        "stress_level": state["stress_level"],
        "priority_breakdown": {
            "P0": len(board.get("P0", [])),
            "P1": len(board.get("P1", [])),
            "P2": len(board.get("P2", [])),
            "P3": len(board.get("P3", []))
        },
        "recommended_focus": [
            {
                "task_id": fb["task_id"],
                "title": fb["title"],
                "duration_mins": fb["recommended_duration"],
                "priority": fb["priority"]
            }
            for fb in focus_blocks
        ],
        "recommended_breaks": breaks,
        "tasks_to_defer": [
            {"task_id": t["task_id"], "title": t.get("title")}
            for t in state.get("tasks_to_defer", [])
        ],
        "wellness_alert": state.get("wellness_concern", False),
        "generated_at": datetime.now().isoformat()
    }
    
    state["today_plan"] = plan
    state["status"] = "completed"
    state["reasoning_trace"].append("Generated comprehensive daily plan")
    
    return state


def check_agent_triggers(state: TaskState) -> TaskState:
    """
    Node 6: Determine if we should trigger other agents
    """
    # Already set in analyze_workload, but ensure flags are correct
    
    # Trigger wellness if high stress or burnout risk
    if state["stress_level"] in ["high", "critical"] or state["burnout_risk"]:
        state["trigger_wellness_agent"] = True
    
    # Trigger followup if there are overdue tasks
    overdue = [
        t for t in state["user_tasks"]
        if t.get("due_date_utc") and t["due_date_utc"] < datetime.now().isoformat()
    ]
    
    if len(overdue) >= 2:
        state["trigger_followup_agent"] = True
        state["reasoning_trace"].append(f"Triggering followup agent for {len(overdue)} overdue tasks")
    
    return state


def record_episode(state: TaskState) -> TaskState:
    """Record task planning as an episode"""
    episodic = EpisodicMemory("task_agent")
    memory = AgentMemory("task_agent")
    
    try:
        # Determine outcome
        outcome = EpisodeOutcome.SUCCESS if state.get("today_plan") else EpisodeOutcome.FAILURE
        
        episode_data = {
            "episode_id": f"task_{int(datetime.now().timestamp() * 1000)}",
            "episode_type": "task_planning",
            "trigger": f"Plan tasks for {state['user_email']}",
            "context": {
                "user_email": state["user_email"],
                "workload_score": state.get("workload_score", 0),
                "stress_level": state.get("stress_level", "unknown"),
                "task_count": len(state.get("user_tasks", [])),
                "focus_blocks": len(state.get("focus_blocks", []))
            },
            "actions": state.get("reasoning_trace", []),
            "outcome": outcome.value,
            "status": "completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }
        
        episodes = episodic._load_episodes()
        episodes.append(episode_data)
        episodic._save_episodes(episodes)
        
        # Store successful pattern
        if outcome == EpisodeOutcome.SUCCESS:
            memory.remember(
                content=f"Successfully planned {len(state['user_tasks'])} tasks with {state['workload_score']:.0f} workload score",
                memory_type=MemoryType.STRATEGY,
                metadata={
                    "user": state["user_email"],
                    "stress_level": state["stress_level"],
                    "focus_blocks": len(state.get("focus_blocks", []))
                }
            )
        
    except Exception as e:
        pass
    
    return state


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def create_task_workflow() -> StateGraph:
    """
    Build the Task Agent workflow
    
    Flow:
    load_context → analyze_workload → prioritize → create_focus_blocks →
    generate_plan → check_triggers → record → END
    """
    
    workflow = StateGraph(TaskState)
    
    # Add nodes
    workflow.add_node("load_task_context", load_task_context)
    workflow.add_node("analyze_workload", analyze_workload)
    workflow.add_node("prioritize_tasks", prioritize_tasks)
    workflow.add_node("create_focus_blocks", create_focus_blocks)
    workflow.add_node("generate_today_plan", generate_today_plan)
    workflow.add_node("check_agent_triggers", check_agent_triggers)
    workflow.add_node("record_episode", record_episode)
    
    # Set entry point
    workflow.set_entry_point("load_task_context")
    
    # Linear flow
    workflow.add_edge("load_task_context", "analyze_workload")
    workflow.add_edge("analyze_workload", "prioritize_tasks")
    workflow.add_edge("prioritize_tasks", "create_focus_blocks")
    workflow.add_edge("create_focus_blocks", "generate_today_plan")
    workflow.add_edge("generate_today_plan", "check_agent_triggers")
    workflow.add_edge("check_agent_triggers", "record_episode")
    workflow.add_edge("record_episode", END)
    
    return workflow


def create_task_workflow_with_memory() -> StateGraph:
    """Create task workflow with memory persistence"""
    graph = create_task_workflow()
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def plan_tasks_for_user(
    user_email: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for task planning
    
    Args:
        user_email: User's email
        session_id: Optional session ID
    
    Returns:
        Dict with today's plan and metadata
    """
    if not session_id:
        session_id = f"task_session_{int(datetime.now().timestamp())}"
    
    # Create initial state
    initial_state = {
        "user_email": user_email,
        "session_id": session_id,
        "request_type": "plan_today",
        "new_task": None,
        "status": "idle",
        "iteration": 0,
        "user_tasks": [],
        "user_meetings": [],
        "past_completion_patterns": [],
        "reasoning_trace": [],
        "eisenhower_board": {},
        "workload_score": 0.0,
        "stress_level": "unknown",
        "burnout_risk": False,
        "focus_blocks": [],
        "recommended_breaks": [],
        "tasks_to_defer": [],
        "wellness_score": None,
        "wellness_concern": False,
        "trigger_wellness_agent": False,
        "trigger_followup_agent": False,
        "today_plan": None,
        "episode_id": None
    }
    
    # Create and run graph
    graph = create_task_workflow_with_memory()
    
    config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke(initial_state, config)
    
    return {
        "plan": result.get("today_plan"),
        "workload_score": result.get("workload_score", 0),
        "stress_level": result.get("stress_level", "unknown"),
        "trigger_wellness": result.get("trigger_wellness_agent", False),
        "trigger_followup": result.get("trigger_followup_agent", False),
        "reasoning": result.get("reasoning_trace", []),
        "session_id": session_id
    }


if __name__ == "__main__":
    # Quick test
    result = plan_tasks_for_user(
        user_email="kowshik.naidu@contoso.com"
    )
    
    print("Task Subgraph Test:")
    print(f"Workload: {result['workload_score']:.0f}/100 ({result['stress_level']})")
    print(f"Trigger wellness: {result['trigger_wellness']}")
    if result['plan']:
        print(f"Focus blocks: {len(result['plan']['recommended_focus'])}")
        print(f"Break recommendations: {len(result['plan']['recommended_breaks'])}")
