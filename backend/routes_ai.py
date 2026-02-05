from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from repos.data_repo import DataRepo
from agents.tasks_agent import TasksAgent
from agents.followup_agent import FollowupAgent
from agents.reporting_agent import ReportingAgent
from agents.wellness_agent import WellnessAgent
from agents.email_agent import EmailAgent
from agents.meeting_agent import MeetingAgent
from orchestration import chat_workflow
from app.smart_chat import SmartChatAgent
from config.settings import SETTINGS
import json

router = APIRouter()

# Keep a cache of SmartChatAgent instances per user
_chat_agents: Dict[str, SmartChatAgent] = {}


@router.post('/ai/plan_today')
async def plan_today(payload: dict):
    user_email = payload.get('user_email')
    if not user_email:
        raise HTTPException(status_code=400, detail='user_email required')
    repo = DataRepo()
    agent = TasksAgent(repo)
    plan = agent.plan_today(user_email)
    return plan


@router.get('/ai/nudges')
async def get_nudges():
    repo = DataRepo()
    agent = FollowupAgent(repo)
    try:
        drafts = agent.nudges()
        return [d.model_dump() if hasattr(d, 'model_dump') else d for d in drafts]
    except Exception as e:
        # Return empty list if nudges fails (e.g., missing data)
        return []


@router.get('/ai/reports/weekly')
async def weekly_reports():
    repo = DataRepo()
    agent = ReportingAgent(repo)
    weeks = agent.weekly()
    return [w.model_dump() if hasattr(w, 'model_dump') else w for w in weeks]


@router.post('/ai/wellness/score')
async def wellness_score(payload: dict):
    user_email = payload.get('user_email')
    if not user_email:
        raise HTTPException(status_code=400, detail='user_email required')
    repo = DataRepo()
    agent = WellnessAgent(repo)
    score = agent.get_wellness_score(user_email)
    return score


@router.post('/assistant/start')
async def assistant_start(payload: dict):
    user_email = payload.get('user_email')
    if not user_email:
        raise HTTPException(status_code=400, detail='user_email required')
    # Create a new SmartChatAgent for this user/session
    repo = DataRepo()
    agent = SmartChatAgent(repo, use_llm=True)
    session_id = agent.context.session_id
    _chat_agents[session_id] = agent
    return {"session_id": session_id}


@router.post('/assistant/chat')
async def assistant_chat(payload: dict):
    session_id = payload.get('session_id')
    user_email = payload.get('user_email')
    message = payload.get('message')
    if not user_email or not message:
        raise HTTPException(status_code=400, detail='user_email and message required')
    
    # Get or create SmartChatAgent
    if session_id and session_id in _chat_agents:
        agent = _chat_agents[session_id]
    else:
        # Create new agent
        repo = DataRepo()
        agent = SmartChatAgent(repo, use_llm=True)
        session_id = agent.context.session_id
        _chat_agents[session_id] = agent
    
    # Use SmartChatAgent's chat_sync for comprehensive response
    try:
        result = agent.chat_sync(message)
        return {
            "response": result.get("content", "I couldn't process that request."),
            "intent": result.get("metadata", {}).get("intent", "unknown"),
            "confidence": result.get("metadata", {}).get("confidence", 0),
            "reasoning_trace": result.get("metadata", {}).get("reasoning_trace", []),
            "session_id": session_id
        }
    except Exception as e:
        import traceback
        print(f"[ERROR] SmartChatAgent failed: {e}")
        traceback.print_exc()
        # Fallback to simple response
        return {
            "response": f"I encountered an issue processing your request. Error: {str(e)}",
            "intent": "error",
            "confidence": 0.8,
            "session_id": session_id
        }


@router.post('/assistant/end')
async def assistant_end(payload: dict):
    session_id = payload.get('session_id')
    if not session_id:
        raise HTTPException(status_code=400, detail='session_id required')
    # Clean up agent
    if session_id in _chat_agents:
        del _chat_agents[session_id]
    return {"status": "ended"}


@router.post('/demo/seed_user')
async def demo_seed_user(payload: dict):
    email = payload.get('email')
    if not email:
        raise HTTPException(status_code=400, detail='email required')
    repo = DataRepo()
    users = repo.users() or []
    if not any(u.get('email') == email for u in users):
        users.append({
            "user_id": f"usr_{email.split('@')[0]}",
            "display_name": email.split('@')[0].replace('.', ' ').title(),
            "email": email,
            "title": "Demo User",
            "department": "Demo",
            "timezone": "UTC",
            "communication_tone": "neutral",
            "sensitivity_clearance": "internal"
        })
        # persist to file
        path = SETTINGS["data"]["users"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(users, indent=2), encoding="utf-8")
    return {"status": "seeded", "email": email}


# ============================================================================
# EMAIL AGENT ENDPOINTS
# ============================================================================

@router.post('/ai/email/analyze')
async def analyze_email(payload: dict):
    """Analyze an email: triage, summarize, extract actions, draft reply"""
    email_id = payload.get('email_id')
    user_email = payload.get('user_email')
    if not email_id or not user_email:
        raise HTTPException(status_code=400, detail='email_id and user_email required')
    repo = DataRepo()
    agent = EmailAgent(repo)
    result = agent.run(email_id, user_email)
    return result.model_dump()


# ============================================================================
# MEETING AGENT ENDPOINTS
# ============================================================================

@router.post('/ai/meeting/mom')
async def generate_meeting_mom(payload: dict):
    """Generate Meeting Minutes/MoM from transcript"""
    meeting_id = payload.get('meeting_id')
    if not meeting_id:
        raise HTTPException(status_code=400, detail='meeting_id required')
    repo = DataRepo()
    agent = MeetingAgent(repo)
    mom = agent.generate_mom(meeting_id)
    return mom.model_dump()


# ============================================================================
# REPORTING AGENT ENDPOINTS
# ============================================================================

@router.get('/ai/reports/eod')
async def get_eod_report():
    """Generate End-of-Day comprehensive report (GET)"""
    repo = DataRepo()
    agent = ReportingAgent(repo)
    eods = agent.eod()
    return [e.model_dump() for e in eods]


@router.post('/ai/reports/eod')
async def generate_eod_report(payload: dict):
    """Generate End-of-Day comprehensive report (POST)"""
    user_email = payload.get('user_email')
    repo = DataRepo()
    agent = ReportingAgent(repo)
    eods = agent.eod()
    return [e.model_dump() for e in eods]


# ============================================================================
# WELLNESS AGENT ENDPOINTS
# ============================================================================

@router.post('/ai/wellness/burnout')
async def check_burnout_risk(payload: dict):
    """Check burnout risk assessment"""
    user_email = payload.get('user_email')
    if not user_email:
        raise HTTPException(status_code=400, detail='user_email required')
    repo = DataRepo()
    agent = WellnessAgent(repo)
    burnout = agent.check_burnout_risk(user_email)
    return burnout.model_dump()


@router.get('/ai/wellness/joke')
async def tell_joke():
    """Tell a joke for stress relief"""
    repo = DataRepo()
    agent = WellnessAgent(repo)
    joke = agent.tell_joke()
    return joke


@router.post('/ai/wellness/break')
async def suggest_break(payload: dict):
    """Suggest a break based on break type"""
    break_type = payload.get('break_type', 'short')  # micro|short|long
    repo = DataRepo()
    agent = WellnessAgent(repo)
    suggestion = agent.suggest_break(break_type)
    return suggestion.model_dump()


@router.post('/ai/wellness/breathing')
async def get_breathing_exercise(payload: dict):
    """Get a breathing exercise for relaxation"""
    exercise_type = payload.get('exercise_type', 'box')  # box|4-7-8|alternate|coherent
    repo = DataRepo()
    agent = WellnessAgent(repo)
    exercise = agent.get_breathing_exercise(exercise_type)
    return exercise


@router.get('/ai/wellness/motivate')
async def get_motivation():
    """Get motivational quote and encouragement"""
    repo = DataRepo()
    agent = WellnessAgent(repo)
    motivation = agent.get_motivation()
    return motivation


@router.post('/ai/wellness/mood')
async def log_mood(payload: dict):
    """Log user mood and get adaptive wellness suggestions"""
    mood = payload.get('mood')  # great|okay|stressed|tired|overwhelmed
    user_email = payload.get('user_email')
    if not mood or not user_email:
        raise HTTPException(status_code=400, detail='mood and user_email required')
    repo = DataRepo()
    agent = WellnessAgent(repo)
    entry = agent.mood_checkin(mood, user_email)
    return entry.model_dump()


@router.get('/ai/wellness/focus_blocks')
async def suggest_focus_blocks():
    """Suggest focus/deep work blocks for the day"""
    repo = DataRepo()
    users = repo.users()
    user_email = users[0]['email'] if users else 'user@example.com'
    agent = WellnessAgent(repo)
    blocks = agent.suggest_focus_blocks(user_email)
    return [b.model_dump() if hasattr(b, 'model_dump') else b for b in blocks]


@router.get('/ai/wellness/meeting_detox')
async def meeting_detox_suggestions():
    """Get meeting optimization and detox suggestions"""
    repo = DataRepo()
    users = repo.users()
    user_email = users[0]['email'] if users else 'user@example.com'
    agent = WellnessAgent(repo)
    suggestions = agent.meeting_detox(user_email)
    return [s.model_dump() if hasattr(s, 'model_dump') else s for s in suggestions]


# ============================================================================
# PROACTIVE ALERTS ENDPOINTS (Phase 3)
# ============================================================================

@router.post('/proactive/notifications')
async def get_user_notifications(payload: dict):
    """Get proactive notifications and alerts for user"""
    user_email = payload.get('user_email')
    if not user_email:
        raise HTTPException(status_code=400, detail='user_email required')
    try:
        from orchestration.proactive_scheduler import get_user_notifications as get_notifs
        notifications = get_notifs(user_email)
        return notifications
    except ImportError:
        return []


@router.post('/proactive/check')
async def run_proactive_check(payload: dict):
    """Run manual proactive wellness check"""
    user_email = payload.get('user_email')
    if not user_email:
        raise HTTPException(status_code=400, detail='user_email required')
    try:
        from orchestration.proactive_scheduler import run_manual_check
        result = run_manual_check(user_email)
        return result
    except ImportError:
        return {"status": "proactive module unavailable"}


# ============================================================================
# AUTONOMOUS AGENT OPERATIONS
# ============================================================================

@router.get('/autonomous/status')
async def autonomous_agent_status():
    """Get status of autonomous inbox processor"""
    try:
        from agents.autonomous_inbox import get_processor_state
        state = get_processor_state()
        return state
    except ImportError:
        return {"is_running": False, "info": "autonomous module not available"}


@router.post('/autonomous/start')
async def start_autonomous_processor():
    """Start the autonomous email processor"""
    try:
        from agents.autonomous_inbox import get_processor
        processor = get_processor()
        processor.start()
        return {"status": "started"}
    except ImportError:
        raise HTTPException(status_code=500, detail="autonomous module not available")


@router.post('/autonomous/stop')
async def stop_autonomous_processor():
    """Stop the autonomous email processor"""
    try:
        from agents.autonomous_inbox import get_processor
        processor = get_processor()
        processor.stop()
        return {"status": "stopped"}
    except ImportError:
        raise HTTPException(status_code=500, detail="autonomous module not available")
