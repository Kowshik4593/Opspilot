# orchestration/meeting_subgraph.py
"""
Meeting Agent Subgraph - Autonomous Meeting Management
======================================================
Transforms meeting processing into an agentic workflow with:
- Automatic transcript analysis
- MoM (Minutes of Meeting) generation with quality checks
- Action item extraction → triggers task agent
- Decision tracking
- Risk/dependency identification
- Learning from past meeting patterns

Makes meetings actually productive for corporate employees!
"""

from __future__ import annotations
from typing import TypedDict, Any, Dict, List, Optional, Annotated
from datetime import datetime
import operator
import json
import re

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Phase 1 imports
from memory import AgentMemory, MemoryType, EpisodicMemory, EpisodeType, EpisodeOutcome
from governance.litellm_gateway import EnhancedLiteLLMGateway
from orchestration.common_state import MeetingWorkflowState, create_initial_state

# Agent imports
from agents.meeting_agent import MeetingAgent
from repos.data_repo import DataRepo


# ============================================================
# STATE DEFINITION
# ============================================================

class MeetingState(TypedDict):
    """State for meeting processing workflow"""
    # Input
    meeting_id: str
    user_email: str
    session_id: str
    
    # Processing state
    status: str  # idle, analyzing, generating_mom, extracting_actions, quality_check, completed
    iteration: int
    max_iterations: int
    
    # Context
    meeting_data: Optional[Dict[str, Any]]
    transcript: Optional[str]
    past_meeting_patterns: List[Dict[str, Any]]
    
    # Agent reasoning
    reasoning_trace: Annotated[List[str], operator.add]
    
    # Analysis results
    meeting_summary: Optional[str]
    key_decisions: List[str]
    action_items: List[Dict[str, Any]]
    risks: List[str]
    dependencies: List[str]
    
    # Quality metrics
    mom_quality_score: float
    completeness_score: float
    
    # Output
    mom: Optional[Dict[str, Any]]
    
    # Cross-agent triggers
    tasks_to_create: List[Dict[str, Any]]
    wellness_concern: bool
    
    # Episode tracking
    episode_id: Optional[str]


# ============================================================
# NODE FUNCTIONS
# ============================================================

def load_meeting_context(state: MeetingState) -> MeetingState:
    """
    Node 1: Load meeting data and recall past patterns
    """
    repo = DataRepo()
    memory = AgentMemory("meeting_agent")
    
    # Load meeting data
    try:
        meetings = repo.meetings()
        meeting = next((m for m in meetings if m.get("meeting_id") == state["meeting_id"]), None)
        
        if meeting:
            state["meeting_data"] = meeting
            state["status"] = "analyzing"
            
            # Load transcript if available
            transcript_path = f"data/mock_data_json/calendar/transcripts/{state['meeting_id']}.txt"
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    state["transcript"] = f.read()
            except:
                state["transcript"] = "No transcript available"
            
            state["reasoning_trace"].append(f"Loaded meeting: {meeting.get('title', 'Untitled')}")
        else:
            state["status"] = "error"
            state["reasoning_trace"].append(f"Meeting {state['meeting_id']} not found")
            return state
    except Exception as e:
        state["status"] = "error"
        state["reasoning_trace"].append(f"Error loading meeting: {str(e)}")
        return state
    
    # Recall past meeting patterns
    try:
        meeting_title = state["meeting_data"].get("title", "")
        attendees = state["meeting_data"].get("attendees", [])
        
        # Check memory for similar meetings
        similar = memory.recall(
            query=f"Past meetings about {meeting_title} with similar attendees",
            n_results=3,
            memory_type=MemoryType.STRATEGY
        )
        
        state["past_meeting_patterns"] = similar
        if similar:
            state["reasoning_trace"].append(f"Found {len(similar)} similar past meetings")
    except:
        state["past_meeting_patterns"] = []
    
    return state


def analyze_meeting(state: MeetingState) -> MeetingState:
    """
    Node 2: Analyze meeting transcript and extract key information
    
    Uses Phase 1 enhanced gateway with caching
    """
    gateway = EnhancedLiteLLMGateway("meeting_agent", enable_cache=True)
    memory = AgentMemory("meeting_agent")
    
    meeting = state.get("meeting_data")
    if not meeting:
        state["status"] = "error"
        state["reasoning_trace"].append("No meeting data available")
        return state
        
    transcript = state.get("transcript", "")
    
    # Build context from past patterns
    past_context = ""
    if state["past_meeting_patterns"]:
        past_context = "\n".join([
            f"- {p['content']}" for p in state["past_meeting_patterns"][:2]
        ])
        past_context = f"\n\nPast Meeting Patterns:\n{past_context}"
    
    # Comprehensive analysis prompt
    prompt = f"""Analyze this meeting and extract structured information.

Meeting: {meeting.get('title', 'Untitled')}
Date: {meeting.get('scheduled_at', 'Unknown')}
Attendees: {', '.join(meeting.get('attendees', []))}
Duration: {meeting.get('duration_mins', 'Unknown')} minutes

Transcript:
{transcript[:3000]}  # Limit for token efficiency
{past_context}

Extract:
1. **Summary** (2-3 sentences of key discussion points)
2. **Decisions** (concrete decisions made, not discussion)
3. **Action Items** (who, what, by when - be specific)
4. **Risks** (any risks or blockers mentioned)
5. **Dependencies** (external dependencies identified)

Return as JSON:
{{
  "summary": "...",
  "decisions": ["decision 1", "decision 2"],
  "action_items": [
    {{"assignee": "person", "action": "task description", "deadline": "date or null"}}
  ],
  "risks": ["risk 1"],
  "dependencies": ["dependency 1"]
}}"""

    try:
        response = gateway.call(
            prompt=prompt,
            temperature=0.3,
            use_cache=True,
            role_context="meeting_analyst"
        )
        
        # Parse response
        analysis = parse_meeting_analysis(response)
        
        state["meeting_summary"] = analysis.get("summary", "")
        state["key_decisions"] = analysis.get("decisions", [])
        state["action_items"] = analysis.get("action_items", [])
        state["risks"] = analysis.get("risks", [])
        state["dependencies"] = analysis.get("dependencies", [])
        
        state["reasoning_trace"].append(
            f"Extracted: {len(state['key_decisions'])} decisions, "
            f"{len(state['action_items'])} actions, {len(state['risks'])} risks"
        )
        
        # Store successful pattern
        if state["action_items"]:
            memory.remember(
                content=f"Meeting '{meeting.get('title')}' typically generates {len(state['action_items'])} action items",
                memory_type=MemoryType.STRATEGY,
                metadata={"meeting_type": meeting.get("title"), "user": state["user_email"]}
            )
        
    except Exception as e:
        state["reasoning_trace"].append(f"Analysis error: {str(e)}")
        # Fallback to basic extraction
        state["meeting_summary"] = "Meeting analysis failed, using fallback."
        state["key_decisions"] = []
        state["action_items"] = []
        state["risks"] = []
        state["dependencies"] = []
    
    state["status"] = "generating_mom"
    return state


def generate_mom(state: MeetingState) -> MeetingState:
    """
    Node 3: Generate structured Minutes of Meeting (MoM)
    """
    meeting = state.get("meeting_data")
    if not meeting:
        state["status"] = "error"
        state["reasoning_trace"].append("Cannot generate MoM without meeting data")
        return state
    
    # Build MoM structure
    mom = {
        "meeting_id": state["meeting_id"],
        "title": meeting.get("title", "Untitled Meeting"),
        "date": meeting.get("scheduled_at", ""),
        "attendees": meeting.get("attendees", []),
        "duration_mins": meeting.get("duration_mins", 0),
        "summary": state.get("meeting_summary", ""),
        "decisions": state.get("key_decisions", []),
        "action_items": state.get("action_items", []),
        "risks": state.get("risks", []),
        "dependencies": state.get("dependencies", []),
        "generated_at": datetime.now().isoformat(),
        "generated_by": "meeting_agent"
    }
    
    state["mom"] = mom
    state["status"] = "quality_check"
    state["reasoning_trace"].append("Generated MoM structure")
    
    return state


def quality_check_mom(state: MeetingState) -> MeetingState:
    """
    Node 4: Assess MoM quality and completeness
    
    Quality criteria:
    - Summary exists and is substantive (>20 chars)
    - At least some structured content (decisions OR actions OR risks)
    - Action items have assignees if present
    """
    mom = state["mom"]
    
    # Quality scoring
    quality_score = 0.0
    
    # Summary quality (0-30 points)
    summary = mom.get("summary", "")
    if len(summary) > 20:
        quality_score += 30
    elif len(summary) > 10:
        quality_score += 15
    
    # Structured content (0-40 points)
    if mom.get("decisions"):
        quality_score += 15
    if mom.get("action_items"):
        quality_score += 15
    if mom.get("risks"):
        quality_score += 10
    
    # Action item completeness (0-30 points)
    action_items = mom.get("action_items", [])
    if action_items:
        complete_actions = sum(
            1 for item in action_items
            if item.get("assignee") and item.get("action")
        )
        quality_score += (complete_actions / len(action_items)) * 30
    
    state["mom_quality_score"] = quality_score / 100.0
    state["completeness_score"] = quality_score / 100.0
    
    state["reasoning_trace"].append(f"Quality score: {quality_score:.0f}/100")
    
    return state


def should_retry_mom(state: MeetingState) -> str:
    """Decision: Is MoM quality acceptable?"""
    quality = state.get("mom_quality_score", 0)
    iteration = state.get("iteration", 0)
    
    # Retry if quality < 0.5 and we haven't exceeded max iterations
    if quality < 0.5 and iteration < state.get("max_iterations", 2):
        state["iteration"] = iteration + 1
        state["reasoning_trace"].append(f"Quality {quality:.2f} insufficient, retrying")
        return "retry"
    
    return "accept"


def extract_task_triggers(state: MeetingState) -> MeetingState:
    """
    Node 5: Identify action items that should trigger task creation
    """
    action_items = state.get("action_items", [])
    
    tasks_to_create = []
    for item in action_items:
        # Only create tasks for action items with clear assignees
        if item.get("assignee") and item.get("action"):
            tasks_to_create.append({
                "title": item["action"],
                "assignee": item["assignee"],
                "deadline": item.get("deadline"),
                "source": "meeting",
                "source_id": state["meeting_id"],
                "priority": "P1"  # Meeting action items are important
            })
    
    state["tasks_to_create"] = tasks_to_create
    state["status"] = "extracting_actions"
    
    if tasks_to_create:
        state["reasoning_trace"].append(f"Identified {len(tasks_to_create)} tasks to create")
    
    return state


def check_wellness_concerns(state: MeetingState) -> MeetingState:
    """
    Node 6: Check if meeting indicates wellness concerns
    
    Signals:
    - Very long meeting (>2 hours)
    - Many risks identified
    - High-stress topics mentioned
    """
    meeting = state["meeting_data"]
    
    wellness_concern = False
    
    # Long meeting check
    duration = meeting.get("duration_mins", 0)
    if duration > 120:
        wellness_concern = True
        state["reasoning_trace"].append(f"Long meeting detected: {duration} mins")
    
    # High risk/stress check
    risks = state.get("risks", [])
    if len(risks) >= 3:
        wellness_concern = True
        state["reasoning_trace"].append(f"High risk count: {len(risks)} risks")
    
    # Stress keywords in summary
    summary = state.get("meeting_summary", "").lower()
    stress_keywords = ["urgent", "critical", "blocker", "delayed", "issue", "problem"]
    if sum(1 for kw in stress_keywords if kw in summary) >= 2:
        wellness_concern = True
        state["reasoning_trace"].append("Stress keywords detected in summary")
    
    state["wellness_concern"] = wellness_concern
    state["status"] = "completed"
    
    return state


def record_episode(state: MeetingState) -> MeetingState:
    """Record this meeting processing as an episode"""
    episodic = EpisodicMemory("meeting_agent")
    
    try:
        # Determine outcome
        outcome = EpisodeOutcome.SUCCESS if state.get("mom") else EpisodeOutcome.FAILURE
        
        episode_data = {
            "episode_id": f"mtg_{int(datetime.now().timestamp() * 1000)}",
            "episode_type": "meeting_processing",
            "trigger": f"Process meeting: {state.get('meeting_id')}",
            "context": {
                "meeting_id": state["meeting_id"],
                "meeting_title": state.get("meeting_data", {}).get("title"),
                "quality_score": state.get("mom_quality_score", 0),
                "actions_extracted": len(state.get("action_items", [])),
                "decisions_captured": len(state.get("key_decisions", []))
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
        
    except Exception as e:
        pass
    
    return state


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_meeting_analysis(llm_response: str) -> Dict[str, Any]:
    """Parse LLM response for meeting analysis"""
    try:
        # Try JSON parsing
        if llm_response.strip().startswith("{"):
            return json.loads(llm_response)
    except:
        pass
    
    # Fallback: heuristic parsing
    result = {
        "summary": "",
        "decisions": [],
        "action_items": [],
        "risks": [],
        "dependencies": []
    }
    
    lines = llm_response.split("\n")
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        lower = line.lower()
        
        # Section detection
        if "summary" in lower and not result["summary"]:
            current_section = "summary"
            # Try to extract summary from same line
            if ":" in line:
                result["summary"] = line.split(":", 1)[1].strip()
            continue
        elif "decision" in lower:
            current_section = "decisions"
            continue
        elif "action" in lower:
            current_section = "action_items"
            continue
        elif "risk" in lower:
            current_section = "risks"
            continue
        elif "depend" in lower:
            current_section = "dependencies"
            continue
        
        # Content extraction
        clean_line = re.sub(r'^[-•*]\s*', '', line)
        
        if current_section == "summary" and not result["summary"]:
            result["summary"] = clean_line
        elif current_section == "decisions":
            result["decisions"].append(clean_line)
        elif current_section == "action_items":
            # Try to parse action item structure
            result["action_items"].append({
                "assignee": "TBD",
                "action": clean_line,
                "deadline": None
            })
        elif current_section == "risks":
            result["risks"].append(clean_line)
        elif current_section == "dependencies":
            result["dependencies"].append(clean_line)
    
    return result


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def create_meeting_workflow() -> StateGraph:
    """
    Build the Meeting Agent workflow
    
    Flow:
    load_context → analyze → generate_mom → quality_check →
    [retry if needed] → extract_tasks → check_wellness → record → END
    """
    
    workflow = StateGraph(MeetingState)
    
    # Add nodes
    workflow.add_node("load_meeting_context", load_meeting_context)
    workflow.add_node("analyze_meeting", analyze_meeting)
    workflow.add_node("generate_mom", generate_mom)
    workflow.add_node("quality_check_mom", quality_check_mom)
    workflow.add_node("extract_task_triggers", extract_task_triggers)
    workflow.add_node("check_wellness_concerns", check_wellness_concerns)
    workflow.add_node("record_episode", record_episode)
    
    # Set entry point
    workflow.set_entry_point("load_meeting_context")
    
    # Linear flow with quality check loop
    workflow.add_edge("load_meeting_context", "analyze_meeting")
    workflow.add_edge("analyze_meeting", "generate_mom")
    workflow.add_edge("generate_mom", "quality_check_mom")
    
    # Conditional: retry or accept MoM?
    workflow.add_conditional_edges(
        "quality_check_mom",
        should_retry_mom,
        {
            "retry": "analyze_meeting",  # Loop back
            "accept": "extract_task_triggers"
        }
    )
    
    workflow.add_edge("extract_task_triggers", "check_wellness_concerns")
    workflow.add_edge("check_wellness_concerns", "record_episode")
    workflow.add_edge("record_episode", END)
    
    return workflow


def create_meeting_workflow_with_memory() -> StateGraph:
    """Create meeting workflow with memory persistence"""
    graph = create_meeting_workflow()
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def process_meeting(
    meeting_id: str,
    user_email: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for processing a meeting
    
    Args:
        meeting_id: ID of the meeting to process
        user_email: User's email
        session_id: Optional session ID
    
    Returns:
        Dict with MoM and metadata
    """
    if not session_id:
        session_id = f"mtg_session_{int(datetime.now().timestamp())}"
    
    # Create initial state
    initial_state = {
        "meeting_id": meeting_id,
        "user_email": user_email,
        "session_id": session_id,
        "status": "idle",
        "iteration": 0,
        "max_iterations": 2,
        "meeting_data": None,
        "transcript": None,
        "past_meeting_patterns": [],
        "reasoning_trace": [],
        "meeting_summary": None,
        "key_decisions": [],
        "action_items": [],
        "risks": [],
        "dependencies": [],
        "mom_quality_score": 0.0,
        "completeness_score": 0.0,
        "mom": None,
        "tasks_to_create": [],
        "wellness_concern": False,
        "episode_id": None
    }
    
    # Create and run graph
    graph = create_meeting_workflow_with_memory()
    
    config = {"configurable": {"thread_id": session_id}}
    result = graph.invoke(initial_state, config)
    
    return {
        "mom": result.get("mom"),
        "quality_score": result.get("mom_quality_score", 0),
        "tasks_to_create": result.get("tasks_to_create", []),
        "wellness_concern": result.get("wellness_concern", False),
        "reasoning": result.get("reasoning_trace", []),
        "session_id": session_id
    }


if __name__ == "__main__":
    # Quick test
    result = process_meeting(
        meeting_id="mtg_311523c4",
        user_email="kowshik.naidu@contoso.com"
    )
    
    print("Meeting Subgraph Test:")
    print(f"Quality: {result['quality_score']:.2f}")
    print(f"Tasks to create: {len(result['tasks_to_create'])}")
    print(f"Wellness concern: {result['wellness_concern']}")
    if result['mom']:
        print(f"Summary: {result['mom']['summary'][:100]}...")
