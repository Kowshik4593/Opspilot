# memory/episodic_memory.py
"""
Episodic Memory System
======================
Tracks complete interaction episodes with outcomes for learning.

Use cases:
- "Last time Sara emailed about API issues, we escalated to DevOps"
- "User typically approves follow-up nudges on Mondays"
- "Meeting MoMs for TechVision project always need detailed technical notes"
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class EpisodeType(str, Enum):
    """Types of episodes"""
    EMAIL_PROCESSING = "email_processing"
    MEETING_ANALYSIS = "meeting_analysis"
    TASK_PLANNING = "task_planning"
    USER_INTERACTION = "user_interaction"
    APPROVAL_DECISION = "approval_decision"


class EpisodeOutcome(str, Enum):
    """Outcome of an episode"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    REJECTED = "rejected"
    APPROVED = "approved"


@dataclass
class Episode:
    """
    A complete interaction episode with context and outcome
    """
    episode_id: str
    episode_type: EpisodeType
    agent_name: str
    
    # Context
    trigger: str  # What initiated this episode
    context: Dict[str, Any]  # Relevant context at start
    
    # Actions taken
    actions: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_trace: List[str] = field(default_factory=list)
    
    # Outcome
    outcome: Optional[EpisodeOutcome] = None
    result: Optional[Dict[str, Any]] = None
    user_feedback: Optional[str] = None
    
    # Metadata
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    
    # Learning signals
    success_factors: List[str] = field(default_factory=list)
    failure_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "episode_type": self.episode_type,
            "agent_name": self.agent_name,
            "trigger": self.trigger,
            "context": self.context,
            "actions": self.actions,
            "reasoning_trace": self.reasoning_trace,
            "outcome": self.outcome,
            "result": self.result,
            "user_feedback": self.user_feedback,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "success_factors": self.success_factors,
            "failure_factors": self.failure_factors
        }


class EpisodicMemory:
    """
    Manages episodic memories for learning from experience
    
    Enables queries like:
    - "How did we handle similar emails from this sender?"
    - "What actions worked well for this type of meeting?"
    - "What did user typically approve/reject?"
    """
    
    def __init__(self, agent_name: str, persist_dir: str = "./episodes"):
        self.agent_name = agent_name
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.episodes_file = self.persist_dir / f"{agent_name}_episodes.json"
        self.episodes: List[Episode] = []
        
        self._load()
    
    def _load(self):
        """Load episodes from disk"""
        if self.episodes_file.exists():
            try:
                data = json.loads(self.episodes_file.read_text(encoding="utf-8"))
                self.episodes = [
                    Episode(**ep) for ep in data
                ]
            except Exception as e:
                print(f"⚠️  Failed to load episodes: {e}")
                self.episodes = []
    
    def _save(self):
        """Save episodes to disk"""
        try:
            data = [ep.to_dict() for ep in self.episodes]
            self.episodes_file.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"⚠️  Failed to save episodes: {e}")
    
    def start_episode(
        self,
        episode_type: EpisodeType,
        trigger: str,
        context: Dict[str, Any],
        episode_id: str = None
    ) -> Episode:
        """Start tracking a new episode"""
        episode = Episode(
            episode_id=episode_id or f"ep_{self.agent_name}_{int(datetime.utcnow().timestamp() * 1000)}",
            episode_type=episode_type,
            agent_name=self.agent_name,
            trigger=trigger,
            context=context
        )
        
        self.episodes.append(episode)
        return episode
    
    def record_action(
        self,
        episode: Episode,
        action: str,
        params: Dict[str, Any],
        result: Optional[Any] = None
    ):
        """Record an action taken during episode"""
        episode.actions.append({
            "action": action,
            "params": params,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def record_reasoning(self, episode: Episode, thought: str):
        """Record reasoning step"""
        episode.reasoning_trace.append(thought)
    
    def complete_episode(
        self,
        episode: Episode,
        outcome: EpisodeOutcome,
        result: Dict[str, Any] = None,
        user_feedback: str = None
    ):
        """Mark episode as complete with outcome"""
        started = datetime.fromisoformat(episode.started_at)
        completed = datetime.utcnow()
        
        episode.completed_at = completed.isoformat()
        episode.duration_seconds = (completed - started).total_seconds()
        episode.outcome = outcome
        episode.result = result
        episode.user_feedback = user_feedback
        
        # Analyze success/failure factors
        self._analyze_episode(episode)
        
        self._save()
    
    def _analyze_episode(self, episode: Episode):
        """Extract learning signals from completed episode"""
        # Simple heuristics for success factors
        if episode.outcome == EpisodeOutcome.SUCCESS:
            episode.success_factors = [
                f"Action sequence: {' -> '.join([a['action'] for a in episode.actions])}",
                f"Context: {list(episode.context.keys())}"
            ]
        elif episode.outcome in [EpisodeOutcome.FAILURE, EpisodeOutcome.REJECTED]:
            episode.failure_factors = [
                f"Failed after {len(episode.actions)} actions",
                f"User feedback: {episode.user_feedback or 'None'}"
            ]
    
    def find_similar(
        self,
        episode_type: EpisodeType,
        context_keys: List[str],
        n_results: int = 5
    ) -> List[Episode]:
        """
        Find similar past episodes
        
        Args:
            episode_type: Type of episode to match
            context_keys: Keys to match in context (e.g., ["sender", "project"])
            n_results: Number of results
        
        Returns:
            List of similar episodes
        """
        matches = []
        
        for ep in self.episodes:
            if ep.episode_type != episode_type:
                continue
            
            if not ep.completed_at:
                continue  # Skip incomplete episodes
            
            # Calculate similarity based on context overlap
            overlap = sum(1 for key in context_keys if key in ep.context)
            if overlap > 0:
                matches.append((ep, overlap))
        
        # Sort by overlap and outcome (prefer successful episodes)
        matches.sort(
            key=lambda x: (x[1], x[0].outcome == EpisodeOutcome.SUCCESS),
            reverse=True
        )
        
        return [ep for ep, _ in matches[:n_results]]
    
    def get_success_patterns(
        self,
        episode_type: EpisodeType,
        min_count: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Extract successful patterns from past episodes
        
        Returns patterns like:
        - "When sender is Sara, escalate P0 issues immediately"
        - "For TechVision meetings, always include technical details in MoM"
        """
        successful = [
            ep for ep in self.episodes
            if ep.episode_type == episode_type
            and ep.outcome == EpisodeOutcome.SUCCESS
            and ep.completed_at
        ]
        
        if len(successful) < min_count:
            return []
        
        # Extract action patterns
        patterns = {}
        for ep in successful:
            action_seq = " -> ".join([a["action"] for a in ep.actions])
            if action_seq in patterns:
                patterns[action_seq]["count"] += 1
                patterns[action_seq]["episodes"].append(ep.episode_id)
            else:
                patterns[action_seq] = {
                    "pattern": action_seq,
                    "count": 1,
                    "episodes": [ep.episode_id],
                    "avg_duration": ep.duration_seconds
                }
        
        # Filter by min_count
        return [
            p for p in patterns.values()
            if p["count"] >= min_count
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about episodes"""
        total = len(self.episodes)
        completed = len([ep for ep in self.episodes if ep.completed_at])
        
        by_outcome = {}
        for ep in self.episodes:
            if ep.outcome:
                by_outcome[ep.outcome] = by_outcome.get(ep.outcome, 0) + 1
        
        return {
            "total_episodes": total,
            "completed": completed,
            "in_progress": total - completed,
            "by_outcome": by_outcome,
            "success_rate": by_outcome.get(EpisodeOutcome.SUCCESS, 0) / completed if completed > 0 else 0
        }
    
    def export(self) -> List[Dict[str, Any]]:
        """Export all episodes"""
        return [ep.to_dict() for ep in self.episodes]


# ============================================================
# DEMO
# ============================================================

def demo_episodic():
    """Demo episodic memory"""
    print("=== Episodic Memory Demo ===\n")
    
    memory = EpisodicMemory("email_agent")
    
    # Start an episode
    print("1. Starting email processing episode...")
    episode = memory.start_episode(
        episode_type=EpisodeType.EMAIL_PROCESSING,
        trigger="New email from Sara about API issue",
        context={
            "sender": "sara@acme.com",
            "subject": "API Gateway timeout",
            "priority": "P0",
            "project": "acme"
        }
    )
    
    # Record actions
    print("2. Recording actions...")
    memory.record_action(episode, "analyze_email", {"email_id": "e123"}, "category: actionable")
    memory.record_reasoning(episode, "Email is critical, need to create task and notify team")
    memory.record_action(episode, "create_task", {"priority": "P0"}, "task_id: t456")
    memory.record_action(episode, "draft_reply", {"tone": "urgent"}, "draft created")
    
    # Complete episode
    print("3. Completing episode...")
    memory.complete_episode(
        episode,
        outcome=EpisodeOutcome.SUCCESS,
        result={"tasks_created": 1, "reply_sent": True},
        user_feedback="Good response time"
    )
    
    # Find similar episodes
    print("\n4. Finding similar episodes...")
    similar = memory.find_similar(
        episode_type=EpisodeType.EMAIL_PROCESSING,
        context_keys=["sender", "priority"],
        n_results=3
    )
    print(f"   Found {len(similar)} similar episodes")
    
    # Get stats
    print("\n5. Episode statistics...")
    stats = memory.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n[OK] Demo complete!")


if __name__ == "__main__":
    demo_episodic()
