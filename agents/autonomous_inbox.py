# agents/autonomous_inbox.py
"""
Autonomous Inbox Processor
==========================
Monitors the inbox for unprocessed emails and automatically processes them
using the ReAct agent or LangGraph workflow.

This is the "always running" component that makes the system truly autonomous.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Generator, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time
import threading
import queue
import uuid

from repos.data_repo import DataRepo
from agents.react_agent import ReActAgent, ReasoningStep, StepType, AgentState
from governance.approval import get_approval_queue, ApprovalPolicy
from orchestration.autonomous_graph import process_email_with_graph


# ============================================================
# EVENT TYPES FOR UI UPDATES
# ============================================================

@dataclass
class AgentEvent:
    """Event emitted by the autonomous processor for UI updates"""
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    event_type: str = ""  # new_email, thinking, action, observation, approval_needed, completed, error
    email_id: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "email_id": self.email_id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


# ============================================================
# PROCESSOR STATE
# ============================================================

@dataclass
class ProcessorState:
    """State of the autonomous processor"""
    is_running: bool = False
    current_email_id: Optional[str] = None
    processed_count: int = 0
    error_count: int = 0
    last_check_time: Optional[str] = None
    events: List[AgentEvent] = field(default_factory=list)
    max_events: int = 100  # Keep last N events
    
    def add_event(self, event: AgentEvent) -> None:
        self.events.append(event)
        # Trim old events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]


# ============================================================
# AUTONOMOUS INBOX PROCESSOR
# ============================================================

class AutonomousInboxProcessor:
    """
    Monitors inbox for new emails and processes them autonomously.
    
    Key features:
    - Polls for unprocessed emails
    - Processes each email through the ReAct agent
    - Emits events for UI updates
    - Queues actions for approval when needed
    """
    
    def __init__(
        self,
        repo: DataRepo = None,
        gateway = None,
        user_email: str = "kowshik.naidu@contoso.com",
        poll_interval: float = 5.0,
        use_langgraph: bool = True
    ):
        self.repo = repo or DataRepo()
        self.gateway = gateway
        self.user_email = user_email
        self.poll_interval = poll_interval
        self.use_langgraph = use_langgraph
        
        self.state = ProcessorState()
        self.event_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[AgentEvent], None]] = []
    
    def add_callback(self, callback: Callable[[AgentEvent], None]) -> None:
        """Add callback to be notified of events"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[AgentEvent], None]) -> None:
        """Remove a callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _emit_event(self, event: AgentEvent) -> None:
        """Emit an event to all callbacks and queue"""
        self.state.add_event(event)
        self.event_queue.put(event)
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass
    
    def start(self) -> None:
        """Start the autonomous processor in background thread"""
        if self.state.is_running:
            return
        
        self._stop_event.clear()
        self.state.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        self._emit_event(AgentEvent(
            event_type="processor_started",
            content="🚀 Autonomous processor started. Monitoring for new emails...",
            metadata={"poll_interval": self.poll_interval}
        ))
    
    def stop(self) -> None:
        """Stop the autonomous processor"""
        self._stop_event.set()
        self.state.is_running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        self._emit_event(AgentEvent(
            event_type="processor_stopped",
            content="⏹️ Autonomous processor stopped."
        ))
    
    def _run_loop(self) -> None:
        """Main processing loop"""
        while not self._stop_event.is_set():
            try:
                self._check_and_process()
            except Exception as e:
                self.state.error_count += 1
                self._emit_event(AgentEvent(
                    event_type="error",
                    content=f"❌ Error in processing loop: {str(e)}",
                    metadata={"error": str(e)}
                ))
            
            # Wait for next poll
            self._stop_event.wait(self.poll_interval)
    
    def _check_and_process(self) -> None:
        """Check for unprocessed emails and process them"""
        self.state.last_check_time = datetime.utcnow().isoformat()
        
        # Get unprocessed emails
        unprocessed = self.repo.get_unprocessed_emails()
        
        if not unprocessed:
            return
        
        self._emit_event(AgentEvent(
            event_type="check_complete",
            content=f"📬 Found {len(unprocessed)} unprocessed email(s)",
            metadata={"count": len(unprocessed)}
        ))
        
        # Process each email
        for email in unprocessed:
            if self._stop_event.is_set():
                break
            
            self._process_single_email(email)
    
    def _process_single_email(self, email: Dict[str, Any]) -> None:
        """Process a single email through the agent"""
        email_id = email.get("email_id", "unknown")
        self.state.current_email_id = email_id
        
        # Emit start event
        self._emit_event(AgentEvent(
            event_type="new_email",
            email_id=email_id,
            content=f"📧 Processing email: {email.get('subject', 'No subject')[:50]}",
            metadata={
                "from": email.get("from_email", "unknown"),
                "subject": email.get("subject", ""),
                "received": email.get("received_utc", "")
            }
        ))
        
        try:
            if self.use_langgraph:
                self._process_with_langgraph(email)
            else:
                self._process_with_react(email)
            
            self.state.processed_count += 1
            
        except Exception as e:
            self.state.error_count += 1
            self._emit_event(AgentEvent(
                event_type="error",
                email_id=email_id,
                content=f"❌ Failed to process email: {str(e)}",
                metadata={"error": str(e)}
            ))
            
            # Mark as processed anyway to avoid infinite loop
            self.repo.mark_email_processed(
                email_id,
                actions_taken=["error"],
                category="error"
            )
        
        self.state.current_email_id = None
    
    def _process_with_langgraph(self, email: Dict[str, Any]) -> None:
        """Process email using LangGraph workflow"""
        email_id = email.get("email_id")
        
        # Run the graph
        final_state = None
        for event in process_email_with_graph(email, self.user_email):
            # Each event is a dict with node name as key
            for node_name, node_state in event.items():
                thought = node_state.get("current_thought", "")
                status = node_state.get("status", "")
                
                # Map to event types
                if node_name == "classify":
                    event_type = "thinking"
                elif node_name == "gather_context":
                    event_type = "action"
                elif node_name == "plan_actions":
                    event_type = "thinking"
                elif node_name == "execute_action":
                    event_type = "action"
                else:
                    event_type = "observation"
                
                if thought:
                    self._emit_event(AgentEvent(
                        event_type=event_type,
                        email_id=email_id,
                        content=thought,
                        metadata={
                            "node": node_name,
                            "status": status,
                            "iteration": node_state.get("iteration", 0)
                        }
                    ))
                
                # Check for pending approvals
                pending = node_state.get("pending_approvals", [])
                for pa in pending:
                    if pa.get("status") == "pending":
                        # Queue for approval
                        approval_queue = get_approval_queue()
                        approval_queue.add_pending_action(
                            action_type=pa.get("action_type"),
                            payload=pa.get("payload", {}),
                            reason=pa.get("reason", "Agent recommended action"),
                            source_email_id=email_id,
                            agent_reasoning=pa.get("description", "")
                        )
                        
                        self._emit_event(AgentEvent(
                            event_type="approval_needed",
                            email_id=email_id,
                            content=f"⏸️ Action queued for approval: {pa.get('action_type')}",
                            metadata={"action": pa}
                        ))
                
                final_state = node_state
        
        # Mark email as processed
        if final_state:
            executed = final_state.get("executed_actions", [])
            category = final_state.get("email_analysis", {}).get("category", "unknown")
            
            self.repo.mark_email_processed(
                email_id,
                actions_taken=executed,
                category=category
            )
            
            self._emit_event(AgentEvent(
                event_type="completed",
                email_id=email_id,
                content=final_state.get("final_summary", "Processing complete"),
                metadata={
                    "actions_executed": len(executed),
                    "category": category,
                    "pending_approvals": len(final_state.get("pending_approvals", []))
                }
            ))
    
    def _process_with_react(self, email: Dict[str, Any]) -> None:
        """Process email using ReAct agent"""
        email_id = email.get("email_id")
        
        # Create agent
        agent = ReActAgent(
            repo=self.repo,
            gateway=self.gateway,
            user_email=self.user_email,
            max_iterations=10
        )
        
        # Process and emit events
        final_state = None
        for step in agent.process_email(email):
            # Map ReasoningStep to AgentEvent
            if step.step_type == StepType.THINK:
                event_type = "thinking"
            elif step.step_type == StepType.ACT:
                event_type = "action"
            elif step.step_type == StepType.OBSERVE:
                event_type = "observation"
            elif step.step_type == StepType.FINISH:
                event_type = "completed"
            elif step.step_type == StepType.AWAIT_APPROVAL:
                event_type = "approval_needed"
            else:
                event_type = "info"
            
            self._emit_event(AgentEvent(
                event_type=event_type,
                email_id=email_id,
                content=step.content,
                metadata={
                    "tool": step.tool_name,
                    "iteration": step.iteration,
                    "result": step.tool_result
                }
            ))
            
            # Handle approval queue
            if step.tool_result and step.tool_result.get("requires_approval"):
                approval_queue = get_approval_queue()
                approval_queue.add_pending_action(
                    action_type=step.tool_name,
                    payload=step.tool_params or {},
                    reason=f"Agent action during email processing",
                    source_email_id=email_id,
                    agent_reasoning=step.content
                )
        
        # The generator returns the final state
        # (Note: In Python, you'd need to catch the return value differently)
        
        # Mark email as processed
        self.repo.mark_email_processed(
            email_id,
            actions_taken=["react_processed"],
            category="processed"
        )
    
    def process_email_now(self, email_id: str) -> Generator[AgentEvent, None, None]:
        """
        Process a specific email immediately (for manual triggering).
        Yields events as they occur.
        """
        # Find the email
        emails = self.repo.inbox()
        email = next((e for e in emails if e.get("email_id") == email_id), None)
        
        if not email:
            yield AgentEvent(
                event_type="error",
                email_id=email_id,
                content=f"Email {email_id} not found"
            )
            return
        
        yield AgentEvent(
            event_type="new_email",
            email_id=email_id,
            content=f"📧 Processing: {email.get('subject', 'No subject')[:50]}",
            metadata={
                "from": email.get("from_email"),
                "subject": email.get("subject")
            }
        )
        
        # Process with LangGraph
        for event in process_email_with_graph(email, self.user_email):
            for node_name, node_state in event.items():
                thought = node_state.get("current_thought", "")
                if thought:
                    yield AgentEvent(
                        event_type="thinking" if "Think" in thought else "observation",
                        email_id=email_id,
                        content=thought,
                        metadata={"node": node_name}
                    )
        
        # Mark processed
        self.repo.mark_email_processed(
            email_id,
            actions_taken=["manual_processed"],
            category="processed"
        )
        
        yield AgentEvent(
            event_type="completed",
            email_id=email_id,
            content="✅ Processing complete"
        )
    
    def get_state(self) -> Dict[str, Any]:
        """Get current processor state for UI"""
        return {
            "is_running": self.state.is_running,
            "current_email_id": self.state.current_email_id,
            "processed_count": self.state.processed_count,
            "error_count": self.state.error_count,
            "last_check_time": self.state.last_check_time,
            "recent_events": [e.to_dict() for e in self.state.events[-20:]]
        }
    
    def get_events(self, since: Optional[str] = None) -> List[AgentEvent]:
        """Get events, optionally filtered by timestamp"""
        if not since:
            return self.state.events[-20:]
        
        return [
            e for e in self.state.events
            if e.timestamp > since
        ]


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_processor: Optional[AutonomousInboxProcessor] = None


def get_processor() -> AutonomousInboxProcessor:
    """Get or create the global processor instance"""
    global _processor
    if _processor is None:
        _processor = AutonomousInboxProcessor()
    return _processor


def start_autonomous_processing() -> None:
    """Start the autonomous processor"""
    processor = get_processor()
    processor.start()


def stop_autonomous_processing() -> None:
    """Stop the autonomous processor"""
    processor = get_processor()
    processor.stop()


def process_email_immediately(email_id: str) -> Generator[AgentEvent, None, None]:
    """Process a specific email immediately"""
    processor = get_processor()
    yield from processor.process_email_now(email_id)


def get_processor_state() -> Dict[str, Any]:
    """Get current processor state"""
    processor = get_processor()
    return processor.get_state()
