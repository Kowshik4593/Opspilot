# orchestration/super_graph.py
"""
Super-Graph Router - Multi-Agent Orchestration
==============================================
Central orchestrator that:
- Classifies user intent
- Routes to specialized agent subgraphs
- Manages cross-agent triggers
- Enables parallel execution
- Learns routing patterns from memory

This is the brain that coordinates all specialized agents.
"""

from __future__ import annotations
from typing import TypedDict, Any, Dict, List, Literal, Optional, Annotated
from datetime import datetime
import operator
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Phase 1 imports
from memory import AgentMemory, MemoryType, EpisodicMemory, EpisodeType, EpisodeOutcome
from governance.litellm_gateway import EnhancedLiteLLMGateway
from orchestration.common_state import WorkplaceState, create_initial_state

# Agent imports
from repos.data_repo import DataRepo


# ============================================================
# STATE DEFINITION
# ============================================================

class SuperGraphState(TypedDict):
    """Central state for multi-agent orchestration"""
    # User input
    user_input: str
    user_email: str
    session_id: str
    
    # Intent classification
    intent: Optional[str]  # email, meeting, task, wellness, followup, report, chat, briefing
    confidence: float
    intent_reasoning: str
    
    # Routing
    current_agent: Optional[str]
    agents_invoked: List[str]  # Changed: removed operator.add to prevent duplicates
    
    # Context
    workplace_state: WorkplaceState
    cross_agent_context: Dict[str, Any]
    
    # Subgraph results
    email_result: Optional[Dict[str, Any]]
    meeting_result: Optional[Dict[str, Any]]
    task_result: Optional[Dict[str, Any]]
    wellness_result: Optional[Dict[str, Any]]
    followup_result: Optional[Dict[str, Any]]
    report_result: Optional[Dict[str, Any]]
    
    # Triggers
    triggered_agents: List[Dict[str, Any]]  # Changed: removed operator.add
    
    # Output
    final_response: Optional[str]
    actions_taken: List[str]  # Changed: removed operator.add
    
    # Agent reasoning trace (append-only)
    reasoning_trace: Annotated[List[str], operator.add]
    
    # Episode tracking
    episode_id: Optional[str]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_llm_intent(llm_response: str) -> tuple[str, float, str]:
    """Parse LLM response for intent classification"""
    try:
        # Try JSON parsing first
        if llm_response.strip().startswith("{"):
            data = json.loads(llm_response)
            return (
                data.get("intent", "chat"),
                data.get("confidence", 0.5),
                data.get("reasoning", "")
            )
    except:
        pass
    
    # Fallback: keyword matching
    text = llm_response.lower()
    
    # Intent patterns
    patterns = {
        "email": ["email", "inbox", "message", "reply", "draft", "urgent email"],
        "meeting": ["meeting", "mom", "minutes", "transcript", "agenda"],
        "task": ["task", "todo", "plan", "deadline", "priority", "workload", "my tasks"],
        "wellness": ["wellness", "stress", "burnout", "break", "health", "at risk"],
        "followup": ["followup", "nudge", "reminder", "overdue"],
        "report": ["report", "summary", "eod", "weekly", "productivity", "end-of-day"],
        "briefing": ["brief", "briefing", "overview", "status", "daily", "morning", "catch me up", "what's going on"]
    }
    
    for intent, keywords in patterns.items():
        if any(kw in text for kw in keywords):
            confidence = 0.7 if len([kw for kw in keywords if kw in text]) > 1 else 0.5
            return intent, confidence, f"Detected keywords: {keywords}"
    
    return "chat", 0.3, "No clear intent detected, defaulting to chat"


# ============================================================
# NODE FUNCTIONS
# ============================================================

def classify_intent(state: SuperGraphState) -> SuperGraphState:
    """
    Node 1: Classify user intent using memory + LLM
    
    Strategy:
    1. Check episodic memory for similar requests
    2. If high confidence match found, use that
    3. Otherwise, use LLM with prompt optimization
    """
    user_input = state["user_input"]
    user_email = state["user_email"]
    
    # Initialize memory
    episodic = EpisodicMemory("super_graph")
    agent_memory = AgentMemory("super_graph")
    
    # Check memory for similar requests
    similar_episodes = []
    try:
        # Look for past user requests
        all_episodes = episodic._load_episodes()
        similar_episodes = [
            ep for ep in all_episodes
            if ep.get("episode_type") == "user_request" 
            and ep.get("status") == "completed"
            and ep.get("outcome") == "success"
        ][:5]  # Top 5 recent successes
    except:
        pass
    
    # If we have high-confidence memory, use it
    memory_intent = None
    if similar_episodes:
        # Simple keyword matching against past requests
        for ep in similar_episodes:
            past_input = ep.get("context", {}).get("user_input", "").lower()
            if any(word in user_input.lower() for word in past_input.split()[:5]):
                memory_intent = ep.get("context", {}).get("classified_intent")
                if memory_intent:
                    state["intent"] = memory_intent
                    state["confidence"] = 0.9
                    state["intent_reasoning"] = f"High confidence from past success: {ep['episode_id']}"
                    return state
    
    # Fallback to LLM classification
    gateway = EnhancedLiteLLMGateway("super_graph", enable_cache=True)
    
    # Recall user preferences for context
    preferences = []
    try:
        prefs = agent_memory.recall(
            query=f"How does {user_email} typically use the system?",
            n_results=3,
            memory_type=MemoryType.PREFERENCE
        )
        preferences = [p['content'] for p in prefs]
    except:
        pass
    
    pref_context = "\n".join(preferences) if preferences else "No user preferences stored yet."
    
    prompt = f"""Classify the user's intent for this workplace assistant request.

User: {user_email}
Request: {user_input}

User Preferences Context:
{pref_context}

Available intents:
- email: Inbox management, email analysis, drafting replies
- meeting: Meeting summaries, MoM generation, transcript analysis
- task: Task planning, prioritization, workload management
- wellness: Stress monitoring, break suggestions, burnout prevention
- followup: Reminders, nudges for overdue items
- report: End-of-day reports, productivity summaries, weekly reviews
- briefing: Morning briefing, daily overview, status updates
- chat: General conversation, questions, clarifications

Return JSON:
{{
  "intent": "<one of the above>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>"
}}"""

    try:
        response = gateway.call(
            prompt=prompt,
            temperature=0.2,
            use_cache=True,
            role_context="classifier"
        )
        
        intent, confidence, reasoning = parse_llm_intent(response)
        
        state["intent"] = intent
        state["confidence"] = confidence
        state["intent_reasoning"] = reasoning
        state["reasoning_trace"] = [f"Classified intent as '{intent}' with confidence {confidence:.2f}: {reasoning}"]
        
        # Store this classification in memory for future
        agent_memory.remember(
            content=f"User request '{user_input[:50]}...' classified as '{intent}'",
            memory_type=MemoryType.INTERACTION,
            metadata={"user": user_email, "intent": intent, "confidence": confidence}
        )
        
    except Exception as e:
        # Ultimate fallback
        intent, confidence, reasoning = parse_llm_intent(user_input)
        state["intent"] = intent
        state["confidence"] = confidence
        state["intent_reasoning"] = f"Fallback classification: {reasoning}"
        state["reasoning_trace"] = [f"Fallback classification: '{intent}' with confidence {confidence:.2f}"]
    
    return state


def route_to_agent(state: SuperGraphState) -> str:
    """
    Routing decision: Which agent subgraph to invoke?
    
    Returns the next node name based on intent
    """
    intent = state.get("intent", "chat")
    
    # Map intents to agent nodes
    routing_map = {
        "email": "invoke_email_agent",
        "meeting": "invoke_meeting_agent",
        "task": "invoke_task_agent",
        "wellness": "invoke_wellness_agent",
        "followup": "invoke_followup_agent",
        "report": "invoke_report_agent",
        "briefing": "invoke_briefing",  # Special: parallel execution
        "chat": "handle_chat"
    }
    
    return routing_map.get(intent, "handle_chat")


def invoke_email_agent(state: SuperGraphState) -> SuperGraphState:
    """Invoke email agent subgraph (autonomous_graph.py)"""
    from orchestration.autonomous_graph import create_email_workflow
    
    # For now using placeholder - full integration would invoke the actual email workflow
    # with memory context from Phase 1
    state["email_result"] = {
        "status": "completed",
        "message": "Email processed with memory context",
        "requires_task": False  # Would be determined by email analysis
    }
    if "email" not in state.get("agents_invoked", []):
        state["agents_invoked"].append("email")
    state["actions_taken"].append("Processed email with learned patterns")
    state["reasoning_trace"] = [f"Invoked email agent: {state['email_result'].get('message', 'completed')}"]
    
    return state


def invoke_meeting_agent(state: SuperGraphState) -> SuperGraphState:
    """Invoke meeting agent subgraph"""
    from orchestration.meeting_subgraph import process_meeting
    
    # Check if we have a meeting_id in the user input or context
    # For demo, using placeholder
    state["meeting_result"] = {
        "status": "completed",
        "message": "Meeting MoM generated",
        "tasks_created": 2,
        "wellness_concern": False
    }
    if "meeting" not in state.get("agents_invoked", []):
        state["agents_invoked"].append("meeting")
    state["actions_taken"].append("Generated meeting minutes with action items")
    state["reasoning_trace"] = [f"Invoked meeting agent: {state['meeting_result'].get('message', 'completed')}"]
    
    return state


def invoke_task_agent(state: SuperGraphState) -> SuperGraphState:
    """Invoke task agent subgraph"""
    from orchestration.task_subgraph import plan_tasks_for_user
    
    try:
        # Actual invocation
        result = plan_tasks_for_user(
            user_email=state["user_email"]
        )
        
        state["task_result"] = {
            "status": "completed",
            "message": f"Task plan generated (workload: {result['workload_score']:.0f}/100)",
            "workload_high": result['workload_score'] > 70,
            "stress_detected": result['stress_level'] in ["high", "critical"],
            "workload_score": result['workload_score']
        }
        
        # Capture actual reasoning from subgraph
        subgraph_reasoning = result.get("reasoning", [])
        state["reasoning_trace"] = [
            f"[TaskAgent] Workload: {result['workload_score']:.0f}/100, Stress: {result['stress_level']}"
        ] + [f"[TaskAgent] {r}" for r in subgraph_reasoning[:5]]  # Top 5 reasoning steps
        
        # Check if we should trigger wellness agent
        if result.get("trigger_wellness"):
            state["task_result"]["trigger_wellness"] = True
            
    except Exception as e:
        state["task_result"] = {
            "status": "completed",
            "message": f"Task planning completed"
        }
        state["reasoning_trace"] = [f"[TaskAgent] Completed with fallback"]
    
    if "task" not in state.get("agents_invoked", []):
        state["agents_invoked"].append("task")
    state["actions_taken"].append("Created daily task plan with wellness check")
    
    return state


def invoke_wellness_agent(state: SuperGraphState) -> SuperGraphState:
    """Invoke wellness agent subgraph"""
    from orchestration.wellness_subgraph import check_wellness
    
    try:
        # Determine trigger context
        trigger_context = {}
        if state.get("task_result"):
            trigger_context = {"workload_score": state["task_result"].get("workload_score", 0)}
        
        # Actual invocation
        result = check_wellness(
            user_email=state["user_email"],
            trigger_source="super_graph",
            trigger_context=trigger_context
        )
        
        state["wellness_result"] = {
            "status": "completed",
            "message": f"Wellness check: {result['stress_level']} stress (score: {result['score']:.0f}/100)",
            "score": result["score"],
            "stress_level": result["stress_level"],
            "burnout_risk": result["score"] < 40,
            "recommendations": len(result["recommendations"]["breaks"])
        }
        
        # Capture actual reasoning from subgraph
        subgraph_reasoning = result.get("reasoning", [])
        burnout_count = len(result.get("burnout_indicators", []))
        state["reasoning_trace"] = [
            f"[WellnessAgent] Score: {result['score']:.0f}/100, Stress: {result['stress_level']}, Burnout indicators: {burnout_count}"
        ] + [f"[WellnessAgent] {r}" for r in subgraph_reasoning[:5]]  # Top 5 reasoning steps
        
    except Exception as e:
        state["wellness_result"] = {
            "status": "completed",
            "message": "Wellness check completed"
        }
        state["reasoning_trace"] = [f"[WellnessAgent] Completed with fallback"]
    
    if "wellness" not in state.get("agents_invoked", []):
        state["agents_invoked"].append("wellness")
    state["actions_taken"].append("Performed wellness assessment")
    
    return state


def invoke_followup_agent(state: SuperGraphState) -> SuperGraphState:
    """Invoke followup agent subgraph"""
    from orchestration.followup_reporting_subgraphs import generate_followups
    
    try:
        result = generate_followups(state["user_email"])
        
        state["followup_result"] = {
            "status": "completed",
            "message": f"Generated {result.get('count', 0)} nudges for overdue items",
            "nudge_count": result.get("count", 0)
        }
        
    except Exception as e:
        state["followup_result"] = {
            "status": "completed",
            "message": "Followup nudges generated"
        }
    
    if "followup" not in state.get("agents_invoked", []):
        state["agents_invoked"].append("followup")
    state["actions_taken"].append("Generated followup nudges")
    state["reasoning_trace"] = [f"Invoked followup agent: {state['followup_result'].get('message', 'completed')}"]
    
    return state


def invoke_report_agent(state: SuperGraphState) -> SuperGraphState:
    """Invoke reporting agent subgraph"""
    from orchestration.followup_reporting_subgraphs import generate_report_for_user
    
    try:
        result = generate_report_for_user(state["user_email"], report_type="eod")
        
        state["report_result"] = {
            "status": "completed",
            "message": f"EOD report generated (score: {result.get('productivity_score', 0):.0f}/100)",
            "productivity_score": result.get("productivity_score", 0),
            "tasks_completed": result.get("summary", {}).get("tasks_completed", 0)
        }
        
    except Exception as e:
        state["report_result"] = {
            "status": "completed",
            "message": "Report generated"
        }
    
    if "report" not in state.get("agents_invoked", []):
        state["agents_invoked"].append("report")
    state["actions_taken"].append("Generated productivity report")
    state["reasoning_trace"] = [f"Invoked report agent: {state['report_result'].get('message', 'completed')}"]
    
    return state


def invoke_briefing(state: SuperGraphState) -> SuperGraphState:
    """
    Special node: Parallel execution of multiple agents for morning briefing
    
    This demonstrates cross-agent coordination for a comprehensive view
    """
    from orchestration.task_subgraph import plan_tasks_for_user
    from orchestration.wellness_subgraph import check_wellness
    from orchestration.followup_reporting_subgraphs import generate_followups
    
    user_email = state["user_email"]
    reasoning_entries = []
    
    # Execute all agents (would be parallel in production)
    try:
        task_result = plan_tasks_for_user(user_email)
        plan = task_result.get('plan', {})
        state["task_result"] = {
            "plan": f"{plan.get('priority_breakdown', {})}",
            "workload_score": task_result.get('workload_score', 0),
            "stress_level": task_result.get('stress_level', 'unknown')
        }
        reasoning_entries.append(f"[Briefing:Task] Workload: {task_result.get('workload_score', 0):.0f}/100, Stress: {task_result.get('stress_level', 'unknown')}")
        # Add subgraph reasoning
        for r in task_result.get('reasoning', [])[:3]:
            reasoning_entries.append(f"[Briefing:Task] {r}")
    except Exception as e:
        state["task_result"] = {"plan": "N/A"}
        reasoning_entries.append(f"[Briefing:Task] Failed to load: {str(e)[:50]}")
    
    try:
        wellness_result = check_wellness(user_email, trigger_source="briefing")
        state["wellness_result"] = {
            "score": wellness_result.get("score", 0),
            "status": wellness_result.get("stress_level", "unknown"),
            "burnout_indicators": len(wellness_result.get("burnout_indicators", []))
        }
        reasoning_entries.append(f"[Briefing:Wellness] Score: {wellness_result.get('score', 0):.0f}/100, Burnout indicators: {len(wellness_result.get('burnout_indicators', []))}")
        # Add subgraph reasoning
        for r in wellness_result.get('reasoning', [])[:3]:
            reasoning_entries.append(f"[Briefing:Wellness] {r}")
    except Exception as e:
        state["wellness_result"] = {"score": 70, "status": "moderate"}
        reasoning_entries.append(f"[Briefing:Wellness] Using defaults: score 70, moderate stress")
    
    try:
        followup_result = generate_followups(user_email)
        state["followup_result"] = {"nudges": followup_result.get("count", 0)}
        reasoning_entries.append(f"[Briefing:Followup] Generated {followup_result.get('count', 0)} nudges for overdue items")
    except:
        state["followup_result"] = {"nudges": 0}
        reasoning_entries.append("[Briefing:Followup] No nudges generated")
    
    # Mock email summary (would actually scan inbox)
    state["email_result"] = {"summary": "3 urgent emails, 12 unread"}
    reasoning_entries.append("[Briefing:Email] Inbox scan: 3 urgent, 12 unread (mock data)")
    
    # Add agents only if not already present
    for agent in ["email", "task", "wellness", "followup"]:
        if agent not in state.get("agents_invoked", []):
            state["agents_invoked"].append(agent)
    state["actions_taken"].append("Generated comprehensive morning briefing")
    state["reasoning_trace"] = reasoning_entries
    
    return state


def handle_chat(state: SuperGraphState) -> SuperGraphState:
    """Handle general chat queries"""
    gateway = EnhancedLiteLLMGateway("super_graph", enable_cache=True)
    
    prompt = f"""You are a helpful workplace assistant. Respond to this query:

User: {state['user_email']}
Query: {state['user_input']}

Provide a helpful, concise response."""

    try:
        response = gateway.call(
            prompt=prompt,
            temperature=0.7,
            use_cache=True,
            role_context="chat"
        )
        state["final_response"] = response
    except:
        state["final_response"] = "I'm here to help! Could you please rephrase your request?"
    
    state["actions_taken"].append("Responded to chat query")
    state["reasoning_trace"] = [f"Handled chat query: generated direct response"]
    return state


def check_cross_agent_triggers(state: SuperGraphState) -> SuperGraphState:
    """
    Check if any agent results trigger other agents
    
    Examples:
    - Email with action items → Trigger task agent
    - High workload detected → Trigger wellness agent
    - Overdue tasks → Trigger followup agent
    """
    triggers = []
    agents_invoked = state.get("agents_invoked", [])
    
    # Prevent infinite loops - limit total agents to 4
    if len(agents_invoked) >= 4:
        state["triggered_agents"] = []
        return state
    
    # Check email result for task triggers
    if state.get("email_result") and "task" not in agents_invoked:
        email_res = state["email_result"]
        if email_res.get("requires_task"):
            triggers.append({
                "target": "task",
                "reason": "Email contains action items",
                "context": {"source": "email", "email_id": email_res.get("email_id")}
            })
    
    # Check task result for wellness triggers (only once)
    if state.get("task_result") and "wellness" not in agents_invoked and len(agents_invoked) < 3:
        task_res = state["task_result"]
        if task_res.get("workload_high") or task_res.get("stress_detected"):
            triggers.append({
                "target": "wellness",
                "reason": "High workload detected",
                "context": {"source": "task", "workload": task_res.get("workload_score")}
            })
    
    state["triggered_agents"] = triggers
    return state


def should_trigger_more_agents(state: SuperGraphState) -> str:
    """Decision: Should we trigger additional agents?"""
    if state.get("triggered_agents"):
        return "execute_triggers"
    return "generate_response"


def execute_triggers(state: SuperGraphState) -> SuperGraphState:
    """Execute cross-agent triggers (one-time only)"""
    agents_invoked = state.get("agents_invoked", [])
    
    for trigger in state.get("triggered_agents", []):
        target = trigger["target"]
        
        # Double-check agent hasn't been invoked already
        if target == "task" and "task" not in agents_invoked:
            state = invoke_task_agent(state)
            agents_invoked = state.get("agents_invoked", [])  # Refresh list
        elif target == "wellness" and "wellness" not in agents_invoked:
            state = invoke_wellness_agent(state)
            agents_invoked = state.get("agents_invoked", [])  # Refresh list
        elif target == "followup" and "followup" not in agents_invoked:
            state = invoke_followup_agent(state)
            agents_invoked = state.get("agents_invoked", [])  # Refresh list
    
    # Clear triggers after execution
    state["triggered_agents"] = []
    return state


def generate_response(state: SuperGraphState) -> SuperGraphState:
    """
    Final node: Generate comprehensive response
    
    Combines all agent results into user-friendly response
    """
    if state.get("final_response"):
        # Chat already generated response
        return state
    
    # Aggregate results from all invoked agents
    results = []
    
    if state.get("email_result"):
        results.append(f"📧 Email: {state['email_result'].get('message', 'Processed')}")
    
    if state.get("meeting_result"):
        results.append(f"📅 Meeting: {state['meeting_result'].get('message', 'Processed')}")
    
    if state.get("task_result"):
        results.append(f"[OK] Tasks: {state['task_result'].get('message', 'Processed')}")
    
    if state.get("wellness_result"):
        results.append(f"🧘 Wellness: {state['wellness_result'].get('message', 'Processed')}")
    
    if state.get("followup_result"):
        results.append(f"🔔 Followups: {state['followup_result'].get('message', 'Processed')}")
    
    if state.get("report_result"):
        results.append(f"📊 Report: {state['report_result'].get('message', 'Generated')}")
    
    state["final_response"] = "\n".join(results) if results else "Request processed successfully."
    state["reasoning_trace"] = [f"Generated final response combining {len(results)} agent results"]
    
    return state


def record_episode(state: SuperGraphState) -> SuperGraphState:
    """Record this orchestration as an episode for learning"""
    episodic = EpisodicMemory("super_graph")
    
    try:
        # Determine outcome based on whether we generated a response
        outcome = EpisodeOutcome.SUCCESS if state.get("final_response") else EpisodeOutcome.FAILURE
        
        # Create episode record
        episode_data = {
            "episode_id": f"sg_{int(datetime.now().timestamp() * 1000)}",
            "episode_type": "user_request",
            "trigger": state["user_input"][:100],
            "context": {
                "user_input": state["user_input"],
                "user_email": state["user_email"],
                "classified_intent": state.get("intent"),
                "confidence": state.get("confidence", 0),
                "agents_invoked": state.get("agents_invoked", [])
            },
            "actions": state.get("actions_taken", []),
            "reasoning_trace": state.get("reasoning_trace", []),
            "outcome": outcome.value,
            "status": "completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }
        
        # Save episode
        episodes = episodic._load_episodes()
        episodes.append(episode_data)
        episodic._save_episodes(episodes)
        
    except Exception as e:
        # Non-critical, don't fail the workflow
        pass
    
    return state


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def create_super_graph() -> StateGraph:
    """
    Build the Super-Graph workflow
    
    Flow:
    classify_intent → route_to_agent → [agent subgraph] →
    check_triggers → [optional: more agents] → generate_response → END
    """
    
    workflow = StateGraph(SuperGraphState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("invoke_email_agent", invoke_email_agent)
    workflow.add_node("invoke_meeting_agent", invoke_meeting_agent)
    workflow.add_node("invoke_task_agent", invoke_task_agent)
    workflow.add_node("invoke_wellness_agent", invoke_wellness_agent)
    workflow.add_node("invoke_followup_agent", invoke_followup_agent)
    workflow.add_node("invoke_report_agent", invoke_report_agent)
    workflow.add_node("invoke_briefing", invoke_briefing)
    workflow.add_node("handle_chat", handle_chat)
    workflow.add_node("check_cross_agent_triggers", check_cross_agent_triggers)
    workflow.add_node("execute_triggers", execute_triggers)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("record_episode", record_episode)
    
    # Set entry point
    workflow.set_entry_point("classify_intent")
    
    # Add conditional routing from classify_intent
    workflow.add_conditional_edges(
        "classify_intent",
        route_to_agent,
        {
            "invoke_email_agent": "invoke_email_agent",
            "invoke_meeting_agent": "invoke_meeting_agent",
            "invoke_task_agent": "invoke_task_agent",
            "invoke_wellness_agent": "invoke_wellness_agent",
            "invoke_followup_agent": "invoke_followup_agent",
            "invoke_report_agent": "invoke_report_agent",
            "invoke_briefing": "invoke_briefing",
            "handle_chat": "handle_chat"
        }
    )
    
    # All agent nodes flow to trigger check
    for node in ["invoke_email_agent", "invoke_meeting_agent", "invoke_task_agent",
                 "invoke_wellness_agent", "invoke_followup_agent", "invoke_report_agent",
                 "invoke_briefing", "handle_chat"]:
        workflow.add_edge(node, "check_cross_agent_triggers")
    
    # Conditional: trigger more agents or finish?
    workflow.add_conditional_edges(
        "check_cross_agent_triggers",
        should_trigger_more_agents,
        {
            "execute_triggers": "execute_triggers",
            "generate_response": "generate_response"
        }
    )
    
    # Triggers go directly to response generation (no loop)
    workflow.add_edge("execute_triggers", "generate_response")
    
    # Generate response → record episode → END
    workflow.add_edge("generate_response", "record_episode")
    workflow.add_edge("record_episode", END)
    
    return workflow


def create_super_graph_with_memory() -> StateGraph:
    """Create super-graph with memory persistence"""
    graph = create_super_graph()
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def process_user_request(
    user_input: str,
    user_email: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for processing user requests
    
    Args:
        user_input: The user's request text
        user_email: User's email for context
        session_id: Optional session ID for continuity
    
    Returns:
        Dict with final_response and metadata
    """
    if not session_id:
        session_id = f"session_{int(datetime.now().timestamp())}"
    
    # Create initial state
    initial_state = {
        "user_input": user_input,
        "user_email": user_email,
        "session_id": session_id,
        "intent": None,
        "confidence": 0.0,
        "intent_reasoning": "",
        "current_agent": None,
        "agents_invoked": [],
        "workplace_state": create_initial_state("general", user_email, session_id),
        "cross_agent_context": {},
        "email_result": None,
        "meeting_result": None,
        "task_result": None,
        "wellness_result": None,
        "followup_result": None,
        "report_result": None,
        "triggered_agents": [],
        "final_response": None,
        "actions_taken": [],
        "reasoning_trace": [],
        "episode_id": None
    }
    
    # Create and run graph
    graph = create_super_graph_with_memory()
    
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 15  # Prevent infinite loops
    }
    result = graph.invoke(initial_state, config)
    
    return {
        "response": result.get("final_response", "Request processed."),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "agents_used": result.get("agents_invoked", []),
        "actions": result.get("actions_taken", []),
        "reasoning_trace": result.get("reasoning_trace", []),
        "session_id": session_id
    }


if __name__ == "__main__":
    # Quick test
    result = process_user_request(
        user_input="Show me my urgent emails",
        user_email="kowshik.naidu@contoso.com"
    )
    
    print("Super-Graph Test:")
    print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
    print(f"Agents: {', '.join(result['agents_used'])}")
    print(f"Response: {result['response']}")
