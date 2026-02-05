# orchestration/wellness_subgraph.py
"""
Wellness Agent Subgraph - Employee Wellbeing & Burnout Prevention
================================================================
Transforms wellness monitoring into an agentic workflow with:
- Real-time workload stress analysis
- Burnout risk detection with early warnings
- Personalized break recommendations
- Meeting detox suggestions
- Focus time protection
- Mood tracking and adaptive responses
- Learning from user's wellness patterns

Keeps corporate employees healthy and productive!
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
from orchestration.common_state import WellnessWorkflowState, create_initial_state

# Agent imports
from agents.wellness_agent import WellnessAgent
from repos.data_repo import DataRepo


# ============================================================
# STATE DEFINITION
# ============================================================

class WellnessState(TypedDict):
    """State for wellness monitoring workflow"""
    # Input
    user_email: str
    session_id: str
    trigger_source: str  # "proactive", "task_agent", "meeting_agent", "user_request"
    trigger_context: Dict[str, Any]
    
    # Processing state
    status: str  # idle, analyzing, detecting_burnout, recommending, completed
    
    # Context
    user_data: Optional[Dict[str, Any]]
    workload_factors: Dict[str, Any]
    recent_patterns: List[Dict[str, Any]]
    
    # Agent reasoning
    reasoning_trace: Annotated[List[str], operator.add]
    
    # Analysis results
    wellness_score: float  # 0-100 (100 = excellent)
    stress_level: str  # low, moderate, high, critical
    burnout_indicators: List[Dict[str, str]]
    risk_factors: List[str]
    
    # Recommendations
    break_suggestions: List[Dict[str, Any]]
    meeting_detox: Optional[Dict[str, Any]]
    focus_protection: Optional[Dict[str, Any]]
    immediate_actions: List[str]
    
    # Approval needed?
    requires_approval: bool
    approval_reason: str
    
    # Output
    wellness_report: Optional[Dict[str, Any]]
    
    # Episode tracking
    episode_id: Optional[str]


# ============================================================
# WORKLOAD FACTORS
# ============================================================

WELLNESS_WEIGHTS = {
    "p0_tasks": 25,
    "overdue_tasks": 20,
    "meeting_load": 20,
    "focus_time": 15,
    "email_backlog": 10,
    "consecutive_work_days": 10
}

BURNOUT_INDICATORS = [
    {
        "name": "high_p0_load",
        "check": lambda factors: factors.get("p0_count", 0) >= 3,
        "severity": "high",
        "message": "Multiple critical P0 tasks creating pressure"
    },
    {
        "name": "chronic_overdue",
        "check": lambda factors: factors.get("overdue_count", 0) >= 3,
        "severity": "high",
        "message": "Chronic backlog of overdue items"
    },
    {
        "name": "meeting_overload",
        "check": lambda factors: factors.get("meeting_hours_today", 0) >= 6,
        "severity": "medium",
        "message": "Excessive meeting time reducing focus opportunities"
    },
    {
        "name": "no_breaks",
        "check": lambda factors: factors.get("hours_without_break", 0) >= 4,
        "severity": "high",
        "message": "Extended work period without breaks"
    },
    {
        "name": "weekend_work",
        "check": lambda factors: factors.get("worked_weekend", False),
        "severity": "medium",
        "message": "Working on weekends reducing recovery time"
    }
]


# ============================================================
# NODE FUNCTIONS
# ============================================================

def load_wellness_context(state: WellnessState) -> WellnessState:
    """
    Node 1: Load user data and wellness history
    """
    repo = DataRepo()
    memory = AgentMemory("wellness_agent")
    
    user_email = state["user_email"]
    
    # Load user
    try:
        users = repo.users()
        user = next((u for u in users if u.get("email") == user_email), None)
        
        if not user:
            state["status"] = "error"
            state["reasoning_trace"].append(f"User {user_email} not found")
            return state
        
        state["user_data"] = user
        state["reasoning_trace"].append(f"Loaded user: {user.get('display_name')}")
        
    except Exception as e:
        state["status"] = "error"
        state["reasoning_trace"].append(f"Error loading user: {str(e)}")
        return state
    
    # Recall past wellness patterns
    try:
        patterns = memory.recall(
            query=f"Wellness patterns and stress indicators for {user_email}",
            n_results=5,
            memory_type=MemoryType.INTERACTION
        )
        
        state["recent_patterns"] = patterns
        if patterns:
            state["reasoning_trace"].append(f"Recalled {len(patterns)} past wellness patterns")
    except:
        state["recent_patterns"] = []
    
    state["status"] = "analyzing"
    return state


def analyze_workload_factors(state: WellnessState) -> WellnessState:
    """
    Node 2: Analyze all workload factors contributing to stress
    """
    repo = DataRepo()
    user_data = state["user_data"]
    user_email = state["user_email"]
    
    # Get user's tasks
    try:
        users = repo.users()
        user = next((u for u in users if u.get("email") == user_email), None)
        user_id = user["user_id"] if user else None
        
        tasks = repo.tasks()
        user_tasks = [t for t in tasks if t.get("owner_user_id") == user_id] if user_id else []
        
        # Active tasks only
        active_tasks = [t for t in user_tasks if t.get("status") not in ["done", "cancelled"]]
        
    except:
        active_tasks = []
    
    # Get meetings
    try:
        meetings = repo.meetings()
        today = datetime.now().date()
        
        user_meetings = [
            m for m in meetings
            if user_email in m.get("attendees", [])
            and m.get("scheduled_at", "").startswith(str(today))
        ]
    except:
        user_meetings = []
    
    # Calculate factors
    factors = {
        "p0_count": len([t for t in active_tasks if t.get("priority") == "P0"]),
        "p1_count": len([t for t in active_tasks if t.get("priority") == "P1"]),
        "overdue_count": len([
            t for t in active_tasks
            if t.get("due_date_utc") and t["due_date_utc"] < datetime.now().isoformat()
        ]),
        "total_tasks": len(active_tasks),
        "meeting_count_today": len(user_meetings),
        "meeting_hours_today": sum(m.get("duration_mins", 30) for m in user_meetings) / 60,
        "hours_without_break": 3,  # Mock - would track from activity
        "worked_weekend": False,  # Mock - would check from history
        "email_backlog": 5  # Mock - would get from inbox
    }
    
    state["workload_factors"] = factors
    
    state["reasoning_trace"].append(
        f"Workload factors: P0={factors['p0_count']}, overdue={factors['overdue_count']}, "
        f"meetings={factors['meeting_hours_today']:.1f}h"
    )
    
    state["status"] = "detecting_burnout"
    return state


def calculate_wellness_score(state: WellnessState) -> WellnessState:
    """
    Node 3: Calculate comprehensive wellness score (0-100)
    
    100 = Excellent wellness
    0 = Critical burnout risk
    """
    factors = state["workload_factors"]
    
    # Start at perfect score and deduct points
    score = 100
    
    # P0 tasks impact (max -25 points)
    p0_impact = min(factors.get("p0_count", 0) * 8, 25)
    score -= p0_impact
    
    # Overdue tasks impact (max -20 points)
    overdue_impact = min(factors.get("overdue_count", 0) * 7, 20)
    score -= overdue_impact
    
    # Meeting overload impact (max -20 points)
    meeting_hours = factors.get("meeting_hours_today", 0)
    if meeting_hours > 4:
        meeting_impact = min((meeting_hours - 4) * 5, 20)
        score -= meeting_impact
    
    # No breaks impact (max -15 points)
    hours_no_break = factors.get("hours_without_break", 0)
    if hours_no_break > 2:
        break_impact = min((hours_no_break - 2) * 5, 15)
        score -= break_impact
    
    # Email backlog impact (max -10 points)
    email_impact = min(factors.get("email_backlog", 0) * 2, 10)
    score -= email_impact
    
    # Weekend work impact (max -10 points)
    if factors.get("worked_weekend", False):
        score -= 10
    
    # Ensure score is in valid range
    score = max(0, min(100, score))
    
    # Determine stress level
    if score >= 80:
        stress_level = "low"
    elif score >= 60:
        stress_level = "moderate"
    elif score >= 40:
        stress_level = "high"
    else:
        stress_level = "critical"
    
    state["wellness_score"] = score
    state["stress_level"] = stress_level
    
    state["reasoning_trace"].append(
        f"Wellness score: {score:.0f}/100 ({stress_level} stress)"
    )
    
    return state


def detect_burnout_indicators(state: WellnessState) -> WellnessState:
    """
    Node 4: Detect specific burnout indicators
    """
    factors = state["workload_factors"]
    
    detected_indicators = []
    risk_factors = []
    
    # Check each burnout indicator
    for indicator in BURNOUT_INDICATORS:
        if indicator["check"](factors):
            detected_indicators.append({
                "name": indicator["name"],
                "severity": indicator["severity"],
                "message": indicator["message"]
            })
            risk_factors.append(indicator["message"])
    
    state["burnout_indicators"] = detected_indicators
    state["risk_factors"] = risk_factors
    
    if detected_indicators:
        high_severity = [i for i in detected_indicators if i["severity"] == "high"]
        state["reasoning_trace"].append(
            f"⚠️ Detected {len(detected_indicators)} burnout indicators "
            f"({len(high_severity)} high severity)"
        )
    
    state["status"] = "recommending"
    return state


def generate_recommendations(state: WellnessState) -> WellnessState:
    """
    Node 5: Generate personalized wellness recommendations
    """
    gateway = EnhancedLiteLLMGateway("wellness_agent", enable_cache=True)
    memory = AgentMemory("wellness_agent")
    
    score = state["wellness_score"]
    stress_level = state["stress_level"]
    indicators = state["burnout_indicators"]
    factors = state["workload_factors"]
    
    # Break suggestions based on stress level
    break_suggestions = []
    
    if stress_level in ["high", "critical"]:
        # Immediate break needed
        break_suggestions.append({
            "type": "immediate_break",
            "duration_mins": 15,
            "urgency": "high",
            "rationale": "High stress detected - immediate break recommended",
            "activity": "Short walk or stretching"
        })
        break_suggestions.append({
            "type": "lunch_break",
            "duration_mins": 45,
            "urgency": "high",
            "rationale": "Extended lunch for recovery",
            "activity": "Away from desk, preferably outdoors"
        })
    
    if stress_level == "moderate":
        break_suggestions.append({
            "type": "microbreak",
            "duration_mins": 5,
            "urgency": "medium",
            "rationale": "Regular microbreaks to maintain energy",
            "activity": "Stand up, look away from screen, hydrate"
        })
    
    # Meeting detox if excessive meetings
    meeting_detox = None
    if factors.get("meeting_hours_today", 0) >= 4:
        meeting_detox = {
            "recommendation": "Block 2-hour focus window tomorrow",
            "rationale": f"{factors['meeting_hours_today']:.1f}h in meetings today - need recovery time",
            "suggested_time": "9:00 AM - 11:00 AM",
            "calendar_block": True
        }
    
    # Focus time protection
    focus_protection = None
    if factors.get("p0_count", 0) >= 2 or factors.get("p1_count", 0) >= 3:
        focus_protection = {
            "recommendation": "Protected focus blocks for critical work",
            "duration_mins": 90,
            "frequency": "daily",
            "rationale": "High-priority tasks require uninterrupted focus"
        }
    
    # Immediate actions for critical cases
    immediate_actions = []
    if stress_level == "critical":
        immediate_actions.append("Take a 15-minute break within the next hour")
        immediate_actions.append("Delegate or defer at least 2 non-critical tasks")
        immediate_actions.append("Notify manager about workload concerns")
        
        # This requires approval
        state["requires_approval"] = True
        state["approval_reason"] = "Critical burnout risk - manager notification recommended"
    
    state["break_suggestions"] = break_suggestions
    state["meeting_detox"] = meeting_detox
    state["focus_protection"] = focus_protection
    state["immediate_actions"] = immediate_actions
    
    state["reasoning_trace"].append(
        f"Generated {len(break_suggestions)} break suggestions, "
        f"meeting_detox={meeting_detox is not None}, "
        f"immediate_actions={len(immediate_actions)}"
    )
    
    # Learn from user preferences
    try:
        past_prefs = memory.recall(
            query=f"Break preferences for {state['user_email']}",
            n_results=3,
            memory_type=MemoryType.PREFERENCE
        )
        
        if past_prefs:
            state["reasoning_trace"].append(
                f"Applied {len(past_prefs)} learned preferences"
            )
    except:
        pass
    
    state["status"] = "completed"
    return state


def create_wellness_report(state: WellnessState) -> WellnessState:
    """
    Node 6: Create comprehensive wellness report
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "user_email": state["user_email"],
        "trigger_source": state["trigger_source"],
        "wellness_score": state["wellness_score"],
        "stress_level": state["stress_level"],
        "burnout_indicators": state["burnout_indicators"],
        "risk_factors": state["risk_factors"],
        "recommendations": {
            "break_suggestions": state["break_suggestions"],
            "meeting_detox": state["meeting_detox"],
            "focus_protection": state["focus_protection"],
            "immediate_actions": state["immediate_actions"]
        },
        "requires_approval": state.get("requires_approval", False),
        "approval_reason": state.get("approval_reason", "")
    }
    
    state["wellness_report"] = report
    state["reasoning_trace"].append("Created comprehensive wellness report")
    
    return state


def record_episode(state: WellnessState) -> WellnessState:
    """Record wellness check as an episode"""
    episodic = EpisodicMemory("wellness_agent")
    memory = AgentMemory("wellness_agent")
    
    try:
        # Determine outcome
        outcome = EpisodeOutcome.SUCCESS if state.get("wellness_report") else EpisodeOutcome.FAILURE
        
        episode_data = {
            "episode_id": f"wellness_{int(datetime.now().timestamp() * 1000)}",
            "episode_type": "wellness_check",
            "trigger": f"Wellness check for {state['user_email']} (source: {state['trigger_source']})",
            "context": {
                "user_email": state["user_email"],
                "trigger_source": state["trigger_source"],
                "wellness_score": state.get("wellness_score", 0),
                "stress_level": state.get("stress_level", "unknown"),
                "burnout_indicators_count": len(state.get("burnout_indicators", [])),
                "recommendations_count": len(state.get("break_suggestions", []))
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
        
        # Store wellness pattern
        if outcome == EpisodeOutcome.SUCCESS:
            memory.remember(
                content=f"Wellness check: {state['stress_level']} stress (score: {state['wellness_score']:.0f})",
                memory_type=MemoryType.INTERACTION,
                metadata={
                    "user": state["user_email"],
                    "score": state["wellness_score"],
                    "stress_level": state["stress_level"]
                }
            )
        
    except Exception as e:
        pass
    
    return state


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def create_wellness_workflow() -> StateGraph:
    """
    Build the Wellness Agent workflow
    
    Flow:
    load_context → analyze_factors → calculate_score →
    detect_burnout → generate_recommendations → create_report → record → END
    """
    
    workflow = StateGraph(WellnessState)
    
    # Add nodes
    workflow.add_node("load_wellness_context", load_wellness_context)
    workflow.add_node("analyze_workload_factors", analyze_workload_factors)
    workflow.add_node("calculate_wellness_score", calculate_wellness_score)
    workflow.add_node("detect_burnout_indicators", detect_burnout_indicators)
    workflow.add_node("generate_recommendations", generate_recommendations)
    workflow.add_node("create_wellness_report", create_wellness_report)
    workflow.add_node("record_episode", record_episode)
    
    # Set entry point
    workflow.set_entry_point("load_wellness_context")
    
    # Linear flow
    workflow.add_edge("load_wellness_context", "analyze_workload_factors")
    workflow.add_edge("analyze_workload_factors", "calculate_wellness_score")
    workflow.add_edge("calculate_wellness_score", "detect_burnout_indicators")
    workflow.add_edge("detect_burnout_indicators", "generate_recommendations")
    workflow.add_edge("generate_recommendations", "create_wellness_report")
    workflow.add_edge("create_wellness_report", "record_episode")
    workflow.add_edge("record_episode", END)
    
    return workflow


def create_wellness_workflow_with_memory() -> StateGraph:
    """Create wellness workflow with memory persistence"""
    graph = create_wellness_workflow()
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def check_wellness(
    user_email: str,
    trigger_source: str = "user_request",
    trigger_context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for wellness checks
    
    Args:
        user_email: User's email
        trigger_source: What triggered this check
        trigger_context: Additional context
        session_id: Optional session ID
    
    Returns:
        Dict with wellness report and recommendations
    """
    if not session_id:
        session_id = f"wellness_session_{int(datetime.now().timestamp())}"
    
    # Create initial state
    initial_state = {
        "user_email": user_email,
        "session_id": session_id,
        "trigger_source": trigger_source,
        "trigger_context": trigger_context or {},
        "status": "idle",
        "user_data": None,
        "workload_factors": {},
        "recent_patterns": [],
        "reasoning_trace": [],
        "wellness_score": 0.0,
        "stress_level": "unknown",
        "burnout_indicators": [],
        "risk_factors": [],
        "break_suggestions": [],
        "meeting_detox": None,
        "focus_protection": None,
        "immediate_actions": [],
        "requires_approval": False,
        "approval_reason": "",
        "wellness_report": None,
        "episode_id": None
    }
    
    # Create and run graph
    graph = create_wellness_workflow_with_memory()
    
    config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke(initial_state, config)
    
    return {
        "report": result.get("wellness_report"),
        "score": result.get("wellness_score", 0),
        "stress_level": result.get("stress_level", "unknown"),
        "burnout_indicators": result.get("burnout_indicators", []),
        "recommendations": {
            "breaks": result.get("break_suggestions", []),
            "meeting_detox": result.get("meeting_detox"),
            "focus_protection": result.get("focus_protection"),
            "immediate_actions": result.get("immediate_actions", [])
        },
        "requires_approval": result.get("requires_approval", False),
        "reasoning": result.get("reasoning_trace", []),
        "session_id": session_id
    }


if __name__ == "__main__":
    # Quick test
    result = check_wellness(
        user_email="kowshik.naidu@contoso.com",
        trigger_source="proactive"
    )
    
    print("Wellness Subgraph Test:")
    print(f"Score: {result['score']:.0f}/100 ({result['stress_level']})")
    print(f"Burnout indicators: {len(result['burnout_indicators'])}")
    print(f"Break suggestions: {len(result['recommendations']['breaks'])}")
    print(f"Requires approval: {result['requires_approval']}")
