# orchestration/chat_workflow.py
"""
Phase 3: Multi-Turn Conversational Chat Workflow
=================================================
Enables natural, multi-turn conversations with context retention.

Features:
- Context retention across turns
- Follow-up question handling
- Clarification requests
- Progressive disclosure
- Conversation history
- Intent switching
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from governance.litellm_gateway import EnhancedLiteLLMGateway
from memory import AgentMemory, EpisodicMemory, MemoryType, EpisodeType, EpisodeOutcome
from orchestration.super_graph import process_user_request


# ============================================================
# CONVERSATION STATE
# ============================================================

@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    turn_id: str
    timestamp: str
    user_message: str
    agent_response: str
    intent: str
    agents_invoked: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChatState(TypedDict):
    """State for chat workflow"""
    # Session
    session_id: str
    user_email: str
    
    # Current turn
    user_input: str
    agent_response: Optional[str]
    
    # Conversation history
    conversation_history: List[ConversationTurn]
    
    # Context
    current_intent: Optional[str]
    last_intent: Optional[str]
    context_summary: str
    
    # Clarification
    needs_clarification: bool
    clarification_question: Optional[str]
    
    # Follow-up detection
    is_followup: bool
    followup_context: Dict[str, Any]
    
    # Multi-step flows
    active_flow: Optional[str]  # e.g., "task_delegation", "meeting_scheduling"
    flow_state: Dict[str, Any]


# ============================================================
# CHAT MANAGER
# ============================================================

class ChatManager:
    """
    Manages multi-turn conversations with context retention
    """
    
    def __init__(self):
        self.gateway = EnhancedLiteLLMGateway("chat_manager", enable_cache=True)
        self.memory = AgentMemory("chat_manager")
        self.sessions: Dict[str, List[ConversationTurn]] = {}
        
    def start_session(self, user_email: str, session_id: Optional[str] = None) -> str:
        """Start a new chat session"""
        if not session_id:
            session_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        self.sessions[session_id] = []
        
        print(f"[CHAT] Started session {session_id} for {user_email}")
        return session_id
    
    def process_message(
        self, 
        session_id: str,
        user_email: str,
        user_input: str
    ) -> Dict[str, Any]:
        """
        Process a message in the conversation
        
        Returns:
            Dict with response, intent, follow_up_suggested, etc.
        """
        history = self.sessions.get(session_id, [])
        
        # Detect if this is a follow-up
        is_followup = self._is_followup(user_input, history)
        
        # Get context from recent turns
        context_summary = self._build_context_summary(history)
        
        # Detect intent (considering context)
        intent = self._detect_intent_with_context(user_input, context_summary, history)
        
        # Check if clarification needed
        needs_clarification, clarification = self._check_clarification_needed(
            user_input, intent, history
        )
        
        if needs_clarification:
            # Return clarification question
            response = clarification
            agents_invoked = []
        else:
            # Process with super-graph
            result = process_user_request(
                user_input=user_input,
                user_email=user_email,
                session_id=session_id
            )
            
            response = result.get("response", "I'm here to help!")
            agents_invoked = result.get("agents_used", [])
        
        # Create turn record
        turn = ConversationTurn(
            turn_id=f"turn_{len(history)+1}",
            timestamp=datetime.now().isoformat(),
            user_message=user_input,
            agent_response=response,
            intent=intent,
            agents_invoked=agents_invoked,
            metadata={
                "is_followup": is_followup,
                "needs_clarification": needs_clarification
            }
        )
        
        # Add to history
        history.append(turn)
        self.sessions[session_id] = history
        
        # Generate follow-up suggestions
        followup_suggestions = self._generate_followup_suggestions(turn, history)
        
        return {
            "response": response,
            "intent": intent,
            "agents_invoked": agents_invoked,
            "is_followup": is_followup,
            "needs_clarification": needs_clarification,
            "followup_suggestions": followup_suggestions,
            "turn_count": len(history),
            "session_id": session_id
        }
    
    def _is_followup(self, user_input: str, history: List[ConversationTurn]) -> bool:
        """Detect if message is a follow-up to previous turn"""
        if not history:
            return False
        
        # Simple heuristics (in production, use LLM)
        followup_keywords = [
            "yes", "no", "okay", "sure", "thanks", "what about",
            "and", "also", "how about", "can you", "please",
            "that", "this", "those", "it", "them"
        ]
        
        lower_input = user_input.lower()
        
        # Short responses are often follow-ups
        if len(user_input.split()) <= 3:
            return True
        
        # Check for follow-up keywords
        for keyword in followup_keywords:
            if lower_input.startswith(keyword):
                return True
        
        return False
    
    def _build_context_summary(self, history: List[ConversationTurn]) -> str:
        """Build summary of recent conversation"""
        if not history:
            return ""
        
        # Last 3 turns
        recent = history[-3:]
        
        summary_parts = []
        for turn in recent:
            summary_parts.append(f"User: {turn.user_message[:80]}")
            summary_parts.append(f"Agent: {turn.agent_response[:80]}")
        
        return "\n".join(summary_parts)
    
    def _detect_intent_with_context(
        self, 
        user_input: str, 
        context: str,
        history: List[ConversationTurn]
    ) -> str:
        """Detect intent considering conversation context"""
        
        # If follow-up, use last intent
        if history and len(user_input.split()) <= 5:
            last_turn = history[-1]
            return last_turn.intent
        
        # Otherwise, detect fresh intent
        prompt = f"""Classify this user request into ONE intent:

Conversation Context:
{context if context else 'New conversation'}

Current Request: {user_input}

Intents: email, meeting, task, wellness, followup, report, briefing, chat

Return ONLY the intent name."""

        try:
            intent = self.gateway.call(
                prompt=prompt,
                temperature=0.2,
                use_cache=True,
                role_context="intent_classification"
            ).strip().lower()
            
            # Validate
            valid_intents = ["email", "meeting", "task", "wellness", "followup", "report", "briefing", "chat"]
            if intent in valid_intents:
                return intent
                
        except:
            pass
        
        return "chat"
    
    def _check_clarification_needed(
        self,
        user_input: str,
        intent: str,
        history: List[ConversationTurn]
    ) -> tuple[bool, Optional[str]]:
        """Check if clarification is needed"""
        
        # Ambiguous requests
        ambiguous_keywords = [
            "help", "something", "stuff", "thing", "what can you do"
        ]
        
        lower_input = user_input.lower()
        
        # Very short or vague requests
        if len(user_input.split()) <= 2:
            for keyword in ambiguous_keywords:
                if keyword in lower_input:
                    return True, "I'd be happy to help! What would you like assistance with? I can help with tasks, meetings, wellness checks, or reports."
        
        # Task intent without specifics
        if intent == "task" and "my tasks" not in lower_input and "plan" not in lower_input:
            return True, "Would you like me to:\n1. Show all your tasks\n2. Create a daily plan\n3. Help with a specific task?"
        
        return False, None
    
    def _generate_followup_suggestions(
        self,
        current_turn: ConversationTurn,
        history: List[ConversationTurn]
    ) -> List[str]:
        """Generate smart follow-up suggestions"""
        suggestions = []
        
        intent = current_turn.intent
        agents = current_turn.agents_invoked
        
        # Intent-based suggestions
        if intent == "task":
            if "wellness" not in agents:
                suggestions.append("Check my wellness score")
            suggestions.append("What about my meetings today?")
            suggestions.append("Any urgent emails?")
        
        elif intent == "wellness":
            suggestions.append("What's causing my stress?")
            suggestions.append("Suggest some breaks")
            suggestions.append("Show my workload")
        
        elif intent == "meeting":
            suggestions.append("Extract action items")
            suggestions.append("Create tasks from this meeting")
            suggestions.append("Check for conflicts")
        
        elif intent == "briefing":
            suggestions.append("Focus on tasks only")
            suggestions.append("Any critical issues?")
            suggestions.append("Compare to yesterday")
        
        # Default suggestions
        if not suggestions:
            suggestions = [
                "What else can you help with?",
                "Show me my priorities",
                "Give me quick tips"
            ]
        
        return suggestions[:3]  # Max 3 suggestions
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        history = self.sessions.get(session_id, [])
        return [
            {
                "turn_id": turn.turn_id,
                "timestamp": turn.timestamp,
                "user_message": turn.user_message,
                "agent_response": turn.agent_response,
                "intent": turn.intent,
                "agents_invoked": turn.agents_invoked
            }
            for turn in history
        ]
    
    def end_session(self, session_id: str):
        """End a chat session"""
        if session_id in self.sessions:
            history = self.sessions[session_id]
            print(f"[CHAT] Ended session {session_id} ({len(history)} turns)")
            
            # Store in memory for learning (with error handling)
            if history:
                try:
                    summary = f"Chat session with {len(history)} turns covering: {', '.join(set(t.intent for t in history))}"
                    self.memory.remember(
                        content=summary,
                        memory_type=MemoryType.INTERACTION,
                        metadata={"session_id": session_id, "turn_count": len(history)}
                    )
                except Exception as e:
                    # Non-critical - don't fail if memory store has issues
                    print(f"[WARN] Could not save chat memory: {e}")
            
            del self.sessions[session_id]


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

_chat_manager: Optional[ChatManager] = None

def get_chat_manager() -> ChatManager:
    """Get or create global chat manager"""
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = ChatManager()
    return _chat_manager


def start_chat(user_email: str) -> str:
    """Start a new chat session"""
    manager = get_chat_manager()
    return manager.start_session(user_email)


def chat(session_id: str, user_email: str, message: str) -> Dict[str, Any]:
    """Send a message in a chat session"""
    manager = get_chat_manager()
    return manager.process_message(session_id, user_email, message)


def get_chat_history(session_id: str) -> List[Dict[str, Any]]:
    """Get chat history"""
    manager = get_chat_manager()
    return manager.get_conversation_history(session_id)


def end_chat(session_id: str):
    """End a chat session"""
    manager = get_chat_manager()
    manager.end_session(session_id)


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    print("="*70)
    print("  Phase 3: Multi-Turn Chat Demo")
    print("="*70)
    
    user = "kowshik.naidu@contoso.com"
    
    # Start chat
    session = start_chat(user)
    print(f"\n[CHAT] Session started: {session}")
    print("[CHAT] Type 'quit' to exit\n")
    
    # Simulate conversation
    test_conversation = [
        "What's my workload today?",
        "That's a lot! What about wellness?",
        "Give me break suggestions",
        "Thanks! Any urgent emails?",
    ]
    
    print("[DEMO] Simulating natural conversation:\n")
    
    for i, message in enumerate(test_conversation, 1):
        print(f"[Turn {i}] You: {message}")
        
        result = chat(session, user, message)
        
        print(f"         Agent: {result['response'][:200]}")
        print(f"         Intent: {result['intent']}")
        print(f"         Agents: {', '.join(result['agents_invoked']) if result['agents_invoked'] else 'None'}")
        
        if result.get('followup_suggestions'):
            print(f"         Suggestions:")
            for suggestion in result['followup_suggestions']:
                print(f"           - {suggestion}")
        
        print()
    
    # Show history
    history = get_chat_history(session)
    print(f"\n[CHAT] Conversation summary:")
    print(f"  Total turns: {len(history)}")
    print(f"  Intents covered: {', '.join(set(t['intent'] for t in history))}")
    print(f"  Agents used: {', '.join(set(a for t in history for a in t['agents_invoked']))}")
    
    # End session
    end_chat(session)
    print(f"\n[OK] Demo complete!")
