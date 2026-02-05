"""
Wellness Agent - Employee wellbeing and sustainable productivity support.

Features:
- Workload analysis & wellness scoring
- Burnout risk detection
- Break & recovery suggestions
- Focus block planning
- Meeting detox recommendations
- Mood check-ins with adaptive responses
- Celebration of wins
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import json
import random
import uuid

from agents.schemas import (
    WellnessScore, WorkloadFactor, BurnoutIndicator, BreakSuggestion,
    FocusBlock, MoodEntry, WellnessNudge, MeetingDetoxSuggestion
)
from agents import prompts
from repos.data_repo import DataRepo
from governance.gateway import PolicyGateway
from governance.audit import write_audit
from config.settings import SETTINGS


class WellnessAgent:
    """
    Agent for employee wellness, stress management, and sustainable productivity.
    Coordinates with other agents to provide holistic wellbeing support.
    """
    
    # Wellness score weights
    WEIGHTS = {
        "p0_tasks": 25,
        "overdue": 20,
        "meetings": 20,
        "focus_time": 15,
        "email_backlog": 10,
        "nudge_pressure": 10
    }
    
    # Thresholds for each factor
    THRESHOLDS = {
        "p0_tasks": {"green": 1, "yellow": 2, "orange": 3, "red": 4},
        "overdue": {"green": 0, "yellow": 1, "orange": 3, "red": 5},
        "meeting_hours": {"green": 3, "yellow": 5, "orange": 6, "red": 7},
        "focus_minutes": {"green": 90, "yellow": 60, "orange": 30, "red": 15},
        "actionable_emails": {"green": 3, "yellow": 6, "orange": 10, "red": 15},
        "critical_nudges": {"green": 1, "yellow": 3, "orange": 5, "red": 7}
    }
    
    # Break suggestions by type
    BREAK_SUGGESTIONS = {
        "micro": [
            BreakSuggestion(break_type="micro", duration_minutes=1, activity="20-20-20 Eye Break",
                          description="Look at something 20 feet away for 20 seconds", emoji="👀"),
            BreakSuggestion(break_type="micro", duration_minutes=1, activity="Deep Breaths",
                          description="Take 5 slow, deep breaths to reset", emoji="🌬️"),
            BreakSuggestion(break_type="micro", duration_minutes=2, activity="Desk Stretch",
                          description="Neck rolls, shoulder shrugs, wrist circles", emoji="🙆"),
        ],
        "short": [
            BreakSuggestion(break_type="short", duration_minutes=5, activity="Hydration Break",
                          description="Walk to get water, refill your bottle", emoji="💧"),
            BreakSuggestion(break_type="short", duration_minutes=5, activity="Quick Walk",
                          description="Walk around the office or step outside briefly", emoji="🚶"),
            BreakSuggestion(break_type="short", duration_minutes=5, activity="Mindful Moment",
                          description="Close eyes, focus on breathing, clear your mind", emoji="🧘"),
        ],
        "long": [
            BreakSuggestion(break_type="long", duration_minutes=15, activity="Coffee/Tea Break",
                          description="Step away, enjoy a warm drink, reset mentally", emoji="☕"),
            BreakSuggestion(break_type="long", duration_minutes=15, activity="Outdoor Walk",
                          description="Get fresh air and sunlight, leave phone behind", emoji="🌳"),
            BreakSuggestion(break_type="long", duration_minutes=10, activity="Social Break",
                          description="Chat with a colleague about non-work topics", emoji="💬"),
        ]
    }
    
    # Tech/work-appropriate jokes
    JOKES = [
        ("Why do programmers prefer dark mode?", "Because light attracts bugs! 🐛"),
        ("Why did the developer go broke?", "Because he used up all his cache! 💸"),
        ("What's a programmer's favorite hangout place?", "Foo Bar! 🍺"),
        ("Why do Java developers wear glasses?", "Because they can't C#! 👓"),
        ("What do you call a computer that sings?", "A-Dell! 🎤"),
        ("Why was the JavaScript developer sad?", "Because he didn't Node how to Express himself! 😢"),
        ("What's a computer's least favorite food?", "Spam! 🥫"),
        ("Why did the SQL query go to therapy?", "It had too many inner joins! 🛋️"),
        ("How many programmers does it take to change a light bulb?", "None, that's a hardware problem! 💡"),
        ("Why do programmers hate nature?", "It has too many bugs and no documentation! 🌲"),
        ("What's a developer's favorite tea?", "Productivi-tea! 🍵"),
        ("Why did the project manager cross the road?", "Because that's what was in the requirements! 📋"),
    ]
    
    # Motivational quotes
    MOTIVATIONAL_QUOTES = [
        ("Progress, not perfection.", "Focus on moving forward, even small steps count."),
        ("You're doing better than you think.", "Imposter syndrome lies. Your work matters."),
        ("One task at a time.", "Multitasking is a myth. Deep focus wins."),
        ("It's okay to not be okay.", "Tough days happen. Be kind to yourself."),
        ("Done is better than perfect.", "Ship it, learn, iterate."),
        ("You've handled hard things before.", "This challenge is no different."),
        ("Take breaks without guilt.", "Rest is productive. Your brain needs it."),
        ("Boundaries are professional.", "Saying no protects your yes."),
        ("Small wins compound.", "Celebrate the little victories."),
        ("You're not behind.", "Everyone's path is different. Trust yours."),
    ]
    
    def __init__(self, repo: DataRepo):
        self.repo = repo
        self.gw = PolicyGateway("wellness_agent")
    
    # ============================================================
    # CORE WELLNESS ASSESSMENT
    # ============================================================
    
    def get_wellness_score(self, user_email: str) -> WellnessScore:
        """Calculate comprehensive wellness score based on workload factors."""
        
        # Gather data
        tasks = self.repo.tasks()
        emails = self.repo.inbox()
        meetings = self.repo.meetings()
        followups = self.repo.followups()
        
        # Find user
        user = self.repo.user_by_email(user_email)
        user_id = user.get("user_id") if user else None
        
        # Filter to user's items
        if user_id:
            user_tasks = [t for t in tasks if t.get("owner_user_id") == user_id]
        else:
            user_tasks = tasks
        
        today = date.today().isoformat()
        
        # Calculate factors
        p0_tasks = [t for t in user_tasks if t.get("priority") == "P0" 
                    and t.get("status") not in ["done", "completed"]]
        p1_tasks = [t for t in user_tasks if t.get("priority") == "P1"
                    and t.get("status") not in ["done", "completed"]]
        overdue_tasks = [t for t in user_tasks 
                        if (t.get("due_date_utc") or "9999")[:10] < today
                        and t.get("status") not in ["done", "completed"]]
        
        # Today's meetings
        today_meetings = [m for m in meetings 
                         if (m.get("scheduled_start_utc") or "")[:10] == today]
        meeting_minutes = sum(
            self._get_meeting_duration(m) for m in today_meetings
        )
        meeting_hours = meeting_minutes / 60
        
        # Calculate focus time (gaps between meetings)
        focus_minutes = self._calculate_focus_time(today_meetings)
        
        # Actionable emails
        actionable_emails = [e for e in emails if e.get("actionability_gt") == "actionable"]
        
        # Critical follow-ups
        critical_followups = [f for f in followups 
                             if f.get("severity") in ["critical", "high"]]
        
        # Build factors and calculate score
        factors = []
        total_deduction = 0
        
        # P0 Tasks factor
        p0_impact = self._calculate_impact("p0_tasks", len(p0_tasks))
        factors.append(WorkloadFactor(
            name="p0_tasks",
            value=len(p0_tasks),
            impact=p0_impact,
            status=self._get_status("p0_tasks", len(p0_tasks)),
            detail=f"{len(p0_tasks)} critical (P0) tasks open"
        ))
        total_deduction += p0_impact
        
        # Overdue factor
        overdue_impact = self._calculate_impact("overdue", len(overdue_tasks))
        factors.append(WorkloadFactor(
            name="overdue",
            value=len(overdue_tasks),
            impact=overdue_impact,
            status=self._get_status("overdue", len(overdue_tasks)),
            detail=f"{len(overdue_tasks)} tasks past due date"
        ))
        total_deduction += overdue_impact
        
        # Meetings factor
        meetings_impact = self._calculate_impact("meetings", meeting_hours)
        factors.append(WorkloadFactor(
            name="meetings",
            value=int(meeting_minutes),
            impact=meetings_impact,
            status=self._get_status("meeting_hours", meeting_hours),
            detail=f"{meeting_hours:.1f} hours of meetings today"
        ))
        total_deduction += meetings_impact
        
        # Focus time factor (inverse - less focus = more impact)
        focus_impact = self._calculate_focus_impact(focus_minutes)
        factors.append(WorkloadFactor(
            name="focus_time",
            value=int(focus_minutes),
            impact=focus_impact,
            status=self._get_focus_status(focus_minutes),
            detail=f"{int(focus_minutes)} min longest focus block"
        ))
        total_deduction += focus_impact
        
        # Email backlog factor
        email_impact = self._calculate_impact("email_backlog", len(actionable_emails))
        factors.append(WorkloadFactor(
            name="email_backlog",
            value=len(actionable_emails),
            impact=email_impact,
            status=self._get_status("actionable_emails", len(actionable_emails)),
            detail=f"{len(actionable_emails)} actionable emails pending"
        ))
        total_deduction += email_impact
        
        # Nudge pressure factor
        nudge_impact = self._calculate_impact("nudge_pressure", len(critical_followups))
        factors.append(WorkloadFactor(
            name="nudge_pressure",
            value=len(critical_followups),
            impact=nudge_impact,
            status=self._get_status("critical_nudges", len(critical_followups)),
            detail=f"{len(critical_followups)} critical/high follow-ups"
        ))
        total_deduction += nudge_impact
        
        # Calculate final score
        score = max(0, min(100, 100 - total_deduction))
        level = self._score_to_level(score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(factors, score)
        
        # Generate summary using LLM or template
        summary = self._generate_wellness_summary(score, level, factors)
        
        result = WellnessScore(
            score=score,
            level=level,
            factors=factors,
            summary=summary,
            recommendations=recommendations,
            timestamp=datetime.utcnow().isoformat()
        )
        
        write_audit("system", "wellness_agent", "calculate_wellness_score",
                   input_refs=[user_email], output_refs=[f"score:{score}"],
                   status="success")
        
        return result
    
    def _calculate_impact(self, factor: str, value: float) -> int:
        """Calculate point deduction for a factor based on value."""
        thresholds = {
            "p0_tasks": [(1, 5), (2, 10), (3, 18), (4, 25)],
            "overdue": [(0, 0), (1, 5), (3, 12), (5, 20)],
            "meetings": [(3, 3), (5, 8), (6, 14), (7, 20)],
            "email_backlog": [(3, 2), (6, 5), (10, 8), (15, 10)],
            "nudge_pressure": [(1, 2), (3, 5), (5, 8), (7, 10)],
        }
        
        if factor not in thresholds:
            return 0
        
        for threshold, impact in thresholds[factor]:
            if value <= threshold:
                return impact
        
        return thresholds[factor][-1][1]  # Max impact
    
    def _calculate_focus_impact(self, focus_minutes: int) -> int:
        """Less focus time = higher impact (inverse relationship)."""
        if focus_minutes >= 90:
            return 0
        elif focus_minutes >= 60:
            return 5
        elif focus_minutes >= 30:
            return 10
        else:
            return 15
    
    def _get_status(self, factor: str, value: float) -> str:
        """Get status color for a factor."""
        t = self.THRESHOLDS.get(factor, {})
        if value <= t.get("green", 0):
            return "green"
        elif value <= t.get("yellow", 0):
            return "yellow"
        elif value <= t.get("orange", 0):
            return "orange"
        return "red"
    
    def _get_focus_status(self, minutes: int) -> str:
        """Get status for focus time (inverse - more is better)."""
        if minutes >= 90:
            return "green"
        elif minutes >= 60:
            return "yellow"
        elif minutes >= 30:
            return "orange"
        return "red"
    
    def _score_to_level(self, score: int) -> str:
        """Convert numeric score to level."""
        if score >= 80:
            return "healthy"
        elif score >= 60:
            return "moderate"
        elif score >= 40:
            return "elevated"
        return "critical"
    
    def _get_meeting_duration(self, meeting: Dict) -> int:
        """Get meeting duration in minutes."""
        try:
            start = datetime.fromisoformat(meeting.get("scheduled_start_utc", "").replace("Z", "+00:00"))
            end = datetime.fromisoformat(meeting.get("scheduled_end_utc", "").replace("Z", "+00:00"))
            return int((end - start).total_seconds() / 60)
        except:
            return 60  # Default 1 hour
    
    def _calculate_focus_time(self, meetings: List[Dict]) -> int:
        """Calculate longest uninterrupted focus block in minutes."""
        if not meetings:
            return 480  # Full 8 hour day
        
        # Sort meetings by start time
        sorted_meetings = sorted(meetings, 
                                key=lambda m: m.get("scheduled_start_utc", ""))
        
        # Assume work day 9am-5pm
        work_start = datetime.now().replace(hour=9, minute=0, second=0)
        work_end = datetime.now().replace(hour=17, minute=0, second=0)
        
        gaps = []
        prev_end = work_start
        
        for m in sorted_meetings:
            try:
                m_start = datetime.fromisoformat(
                    m.get("scheduled_start_utc", "").replace("Z", "+00:00")
                ).replace(tzinfo=None)
                m_end = datetime.fromisoformat(
                    m.get("scheduled_end_utc", "").replace("Z", "+00:00")
                ).replace(tzinfo=None)
                
                gap = (m_start - prev_end).total_seconds() / 60
                if gap > 0:
                    gaps.append(gap)
                prev_end = max(prev_end, m_end)
            except:
                continue
        
        # Gap after last meeting
        final_gap = (work_end - prev_end).total_seconds() / 60
        if final_gap > 0:
            gaps.append(final_gap)
        
        return int(max(gaps)) if gaps else 60
    
    def _generate_recommendations(self, factors: List[WorkloadFactor], score: int) -> List[str]:
        """Generate actionable recommendations based on factors."""
        recs = []
        
        for f in factors:
            if f.status in ["orange", "red"]:
                if f.name == "p0_tasks":
                    recs.append(f"Focus on one P0 task at a time — multitasking increases stress")
                elif f.name == "overdue":
                    recs.append(f"Address overdue items first, or communicate new deadlines")
                elif f.name == "meetings":
                    recs.append(f"Consider declining optional meetings or requesting async updates")
                elif f.name == "focus_time":
                    recs.append(f"Block 60+ minutes for deep work — protect your focus time")
                elif f.name == "email_backlog":
                    recs.append(f"Batch process emails in 2-3 dedicated slots, not continuously")
                elif f.name == "nudge_pressure":
                    recs.append(f"Delegate or escalate some follow-ups to reduce pressure")
        
        if score < 50:
            recs.append("Take a 15-minute break to reset — you're running hot")
        
        return recs[:4]  # Max 4 recommendations
    
    def _generate_wellness_summary(self, score: int, level: str, 
                                   factors: List[WorkloadFactor]) -> str:
        """Generate a human-friendly wellness summary."""
        # Find the most impactful factors
        sorted_factors = sorted(factors, key=lambda f: f.impact, reverse=True)
        top_issue = sorted_factors[0] if sorted_factors else None
        
        if level == "healthy":
            return f"You're in good shape! Your workload is balanced with a score of {score}/100. Keep up the sustainable pace."
        elif level == "moderate":
            return f"Manageable workload (score: {score}/100). Watch your {top_issue.name.replace('_', ' ')} — {top_issue.detail.lower()}."
        elif level == "elevated":
            return f"Elevated stress detected (score: {score}/100). Main concern: {top_issue.detail.lower()}. Consider taking action to rebalance."
        else:
            return f"⚠️ High stress alert (score: {score}/100). Multiple factors need attention. Please prioritize self-care and consider escalating or delegating tasks."
    
    # ============================================================
    # BURNOUT DETECTION
    # ============================================================
    
    def check_burnout_risk(self, user_email: str, days: int = 5) -> BurnoutIndicator:
        """Assess burnout risk based on recent patterns."""
        
        # Get wellness score as baseline
        wellness = self.get_wellness_score(user_email)
        
        signals = []
        
        # Check for chronic overload signals
        for f in wellness.factors:
            if f.status == "red":
                signals.append(f"🔴 Critical: {f.detail}")
            elif f.status == "orange":
                signals.append(f"🟠 Warning: {f.detail}")
        
        # Additional heuristic checks
        tasks = self.repo.tasks()
        user = self.repo.user_by_email(user_email)
        user_id = user.get("user_id") if user else None
        
        if user_id:
            user_tasks = [t for t in tasks if t.get("owner_user_id") == user_id]
            
            # Check for task pile-up
            open_tasks = [t for t in user_tasks if t.get("status") not in ["done", "completed"]]
            if len(open_tasks) > 10:
                signals.append(f"📋 {len(open_tasks)} open tasks — potential overwhelm")
            
            # Check for blocked tasks
            blocked = [t for t in user_tasks if t.get("status") == "blocked"]
            if len(blocked) > 2:
                signals.append(f"🚫 {len(blocked)} blocked tasks — frustration risk")
        
        # Determine risk level
        red_count = sum(1 for f in wellness.factors if f.status == "red")
        orange_count = sum(1 for f in wellness.factors if f.status == "orange")
        
        if red_count >= 3 or wellness.score < 30:
            risk_level = "critical"
        elif red_count >= 2 or wellness.score < 45:
            risk_level = "high"
        elif red_count >= 1 or orange_count >= 3 or wellness.score < 60:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate recommendations
        recommendations = []
        if risk_level in ["critical", "high"]:
            recommendations = [
                "Consider talking to your manager about workload",
                "Delegate or defer non-critical tasks",
                "Take a proper lunch break away from your desk",
                "Block tomorrow morning for catch-up, no meetings"
            ]
        elif risk_level == "medium":
            recommendations = [
                "Prioritize ruthlessly — say no to new requests",
                "Take short breaks between tasks",
                "End work at a fixed time today"
            ]
        else:
            recommendations = [
                "Maintain your current sustainable pace",
                "Keep protecting your focus time"
            ]
        
        result = BurnoutIndicator(
            risk_level=risk_level,
            signals=signals[:6],
            days_analyzed=days,
            recommendations=recommendations
        )
        
        write_audit("system", "wellness_agent", "check_burnout_risk",
                   input_refs=[user_email], output_refs=[f"risk:{risk_level}"],
                   status="success")
        
        return result
    
    # ============================================================
    # BREAK & RECOVERY SUGGESTIONS
    # ============================================================
    
    def suggest_break(self, break_type: str = "short", context: str = "") -> BreakSuggestion:
        """Suggest a break activity based on type and context."""
        
        if break_type not in self.BREAK_SUGGESTIONS:
            break_type = "short"
        
        # Random selection from appropriate type
        suggestion = random.choice(self.BREAK_SUGGESTIONS[break_type])
        
        write_audit("system", "wellness_agent", "suggest_break",
                   input_refs=[break_type], output_refs=[suggestion.activity],
                   status="success")
        
        return suggestion
    
    def get_all_break_suggestions(self) -> Dict[str, List[BreakSuggestion]]:
        """Get all break suggestions organized by type."""
        return self.BREAK_SUGGESTIONS
    
    # ============================================================
    # JOKES & MOTIVATION
    # ============================================================
    
    def tell_joke(self) -> Dict[str, str]:
        """Return a random work-appropriate joke."""
        setup, punchline = random.choice(self.JOKES)
        
        write_audit("system", "wellness_agent", "tell_joke",
                   input_refs=[], output_refs=["joke_delivered"],
                   status="success")
        
        return {
            "setup": setup,
            "punchline": punchline,
            "full": f"{setup}\n\n{punchline}"
        }
    
    def get_motivation(self, context: str = "") -> Dict[str, str]:
        """Return a motivational quote with explanation."""
        quote, explanation = random.choice(self.MOTIVATIONAL_QUOTES)
        
        write_audit("system", "wellness_agent", "get_motivation",
                   input_refs=[], output_refs=["motivation_delivered"],
                   status="success")
        
        return {
            "quote": quote,
            "explanation": explanation,
            "full": f"💪 **{quote}**\n\n_{explanation}_"
        }
    
    # ============================================================
    # BREATHING EXERCISES
    # ============================================================
    
    def get_breathing_exercise(self, exercise_type: str = "box") -> Dict[str, Any]:
        """Get a guided breathing exercise."""
        
        exercises = {
            "box": {
                "name": "Box Breathing",
                "description": "A calming technique used by Navy SEALs to reduce stress",
                "duration_minutes": 2,
                "steps": [
                    "🌬️ Breathe IN through your nose for 4 counts",
                    "⏸️ HOLD your breath for 4 counts",
                    "💨 Breathe OUT through your mouth for 4 counts",
                    "⏸️ HOLD empty for 4 counts",
                    "🔄 Repeat 4-6 times"
                ],
                "emoji": "📦"
            },
            "478": {
                "name": "4-7-8 Breathing",
                "description": "A relaxation technique that promotes calmness",
                "duration_minutes": 3,
                "steps": [
                    "🌬️ Breathe IN quietly through your nose for 4 counts",
                    "⏸️ HOLD your breath for 7 counts",
                    "💨 Breathe OUT completely through mouth for 8 counts",
                    "🔄 Repeat 3-4 times"
                ],
                "emoji": "🧘"
            },
            "quick": {
                "name": "Quick Reset Breath",
                "description": "A fast stress-relief technique for busy moments",
                "duration_minutes": 1,
                "steps": [
                    "🌬️ Take a deep breath IN for 3 counts",
                    "💨 Sigh OUT loudly, releasing tension",
                    "🔄 Repeat 3 times"
                ],
                "emoji": "⚡"
            }
        }
        
        exercise = exercises.get(exercise_type, exercises["box"])
        
        write_audit("system", "wellness_agent", "breathing_exercise",
                   input_refs=[exercise_type], output_refs=[exercise["name"]],
                   status="success")
        
        return exercise
    
    # ============================================================
    # MOOD CHECK-IN
    # ============================================================
    
    def mood_checkin(self, mood: str, user_email: str, notes: str = "") -> MoodEntry:
        """Record a mood check-in and provide adaptive response."""
        
        mood_map = {
            "great": ("😊", "That's wonderful to hear!"),
            "okay": ("😐", "Steady is good. Let me know if you need anything."),
            "stressed": ("😫", "I hear you. Let's see what we can do to help."),
            "tired": ("😴", "Rest is important. Consider a short break."),
            "overwhelmed": ("🤯", "That's tough. Let's look at your workload together.")
        }
        
        emoji, _ = mood_map.get(mood.lower(), ("😐", "Thanks for checking in."))
        
        entry = MoodEntry(
            mood=mood.lower(),
            emoji=emoji,
            timestamp=datetime.utcnow().isoformat(),
            notes=notes if notes else None,
            adjustments_made=[]
        )
        
        # If mood is negative, suggest adjustments
        if mood.lower() in ["stressed", "tired", "overwhelmed"]:
            entry.adjustments_made = [
                "Consider taking a 5-minute break",
                "Focus on just one task at a time",
                "It's okay to push non-urgent items to tomorrow"
            ]
        
        write_audit("system", "wellness_agent", "mood_checkin",
                   input_refs=[user_email, mood], output_refs=["mood_recorded"],
                   status="success")
        
        return entry
    
    # ============================================================
    # FOCUS BLOCKS
    # ============================================================
    
    def suggest_focus_blocks(self, user_email: str) -> List[FocusBlock]:
        """Suggest focus/deep work blocks based on calendar gaps."""
        
        meetings = self.repo.meetings()
        today = date.today().isoformat()
        
        # Get today's meetings
        today_meetings = [m for m in meetings 
                        if (m.get("scheduled_start_utc") or "")[:10] == today]
        
        # Sort by start time
        sorted_meetings = sorted(today_meetings,
                                key=lambda m: m.get("scheduled_start_utc", ""))
        
        # Find gaps
        focus_blocks = []
        work_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        work_end = datetime.now().replace(hour=17, minute=0, second=0, microsecond=0)
        
        prev_end = work_start
        
        for m in sorted_meetings:
            try:
                m_start = datetime.fromisoformat(
                    m.get("scheduled_start_utc", "").replace("Z", "+00:00")
                ).replace(tzinfo=None)
                
                gap_minutes = (m_start - prev_end).total_seconds() / 60
                
                if gap_minutes >= 30:  # Only suggest blocks >= 30 min
                    # Cap duration at 120 minutes for better focus
                    capped_duration = min(int(gap_minutes), 120)
                    focus_blocks.append(FocusBlock(
                        start_time=prev_end.strftime("%H:%M"),
                        end_time=(prev_end + timedelta(minutes=capped_duration)).strftime("%H:%M"),
                        duration_minutes=capped_duration,
                        block_type="deep_work" if capped_duration >= 60 else "pomodoro",
                        suggested_task="Priority task work"
                    ))
                
                m_end = datetime.fromisoformat(
                    m.get("scheduled_end_utc", "").replace("Z", "+00:00")
                ).replace(tzinfo=None)
                prev_end = max(prev_end, m_end)
            except:
                continue
        
        # Check for gap after last meeting
        final_gap = (work_end - prev_end).total_seconds() / 60
        if final_gap >= 30:
            # Cap blocks at 120 minutes max for better focus
            capped_duration = min(int(final_gap), 120)
            focus_blocks.append(FocusBlock(
                start_time=prev_end.strftime("%H:%M"),
                end_time=(prev_end + timedelta(minutes=capped_duration)).strftime("%H:%M"),
                duration_minutes=capped_duration,
                block_type="deep_work" if capped_duration >= 60 else "pomodoro",
                suggested_task="End-of-day priority task completion"
            ))
        
        # If no blocks found but time available, suggest reasonable focus blocks
        if not focus_blocks:
            # Suggest 2 focus blocks during optimal times
            focus_blocks = [
                FocusBlock(
                    start_time="09:00",
                    end_time="11:00",
                    duration_minutes=120,
                    block_type="deep_work",
                    suggested_task="High-priority task review"
                ),
                FocusBlock(
                    start_time="14:00",
                    end_time="16:00",
                    duration_minutes=120,
                    block_type="deep_work",
                    suggested_task="Project development work"
                )
            ]
        
        write_audit("system", "wellness_agent", "suggest_focus_blocks",
                   input_refs=[user_email], output_refs=[f"blocks:{len(focus_blocks)}"],
                   status="success")
        
        return focus_blocks[:5]  # Max 5 blocks
    
    # ============================================================
    # MEETING DETOX
    # ============================================================
    
    def meeting_detox(self, user_email: str) -> List[MeetingDetoxSuggestion]:
        """Analyze meetings and suggest optimizations."""
        
        meetings = self.repo.meetings()
        today = date.today().isoformat()
        
        # Get upcoming meetings
        upcoming = [m for m in meetings 
                   if (m.get("scheduled_start_utc") or "") >= today
                   and m.get("status") != "completed"]
        
        suggestions = []
        
        for m in upcoming:
            meeting_id = m.get("meeting_id", "")
            title = m.get("title", "Untitled")
            duration = self._get_meeting_duration(m)
            agenda = m.get("agenda", "")
            
            # No agenda → suggest async
            if not agenda or agenda.strip() == "":
                suggestions.append(MeetingDetoxSuggestion(
                    meeting_id=meeting_id,
                    meeting_title=title,
                    suggestion_type="async",
                    reason="No agenda set — could this be an email or async update?",
                    potential_time_saved_minutes=duration
                ))
            
            # Long meeting → suggest shortening
            elif duration > 60:
                suggestions.append(MeetingDetoxSuggestion(
                    meeting_id=meeting_id,
                    meeting_title=title,
                    suggestion_type="shorten",
                    reason=f"{duration} min is long — could it be done in 45 min?",
                    potential_time_saved_minutes=duration - 45
                ))
            
            # Back-to-back meetings → suggest buffer
            # (simplified check)
            elif "sync" in title.lower() or "standup" in title.lower():
                suggestions.append(MeetingDetoxSuggestion(
                    meeting_id=meeting_id,
                    meeting_title=title,
                    suggestion_type="add_buffer",
                    reason="Regular sync — consider adding 5-min buffer after",
                    potential_time_saved_minutes=0
                ))
        
        write_audit("system", "wellness_agent", "meeting_detox",
                   input_refs=[user_email], output_refs=[f"suggestions:{len(suggestions)}"],
                   status="success")
        
        return suggestions[:5]
    
    # ============================================================
    # PROACTIVE WELLNESS NUDGES
    # ============================================================
    
    def generate_wellness_nudges(self, user_email: str) -> List[WellnessNudge]:
        """Generate proactive wellness nudges based on current state."""
        
        wellness = self.get_wellness_score(user_email)
        nudges = []
        
        # Critical workload nudge
        if wellness.level == "critical":
            nudges.append(WellnessNudge(
                nudge_id=f"wellness_{uuid.uuid4().hex[:8]}",
                nudge_type="burnout",
                severity="critical",
                title="⚠️ High Stress Detected",
                message=f"Your wellness score is {wellness.score}/100. {wellness.summary}",
                suggested_action="Consider taking a break and reviewing your priorities"
            ))
        
        # Break reminder nudge
        for f in wellness.factors:
            if f.name == "focus_time" and f.status in ["orange", "red"]:
                nudges.append(WellnessNudge(
                    nudge_id=f"wellness_{uuid.uuid4().hex[:8]}",
                    nudge_type="focus",
                    severity="warning",
                    title="🧠 Limited Focus Time",
                    message=f"Your longest focus block today is only {f.value} minutes. Deep work needs 60+ minutes.",
                    suggested_action="Block 60 minutes on your calendar for focused work"
                ))
            
            if f.name == "meetings" and f.status == "red":
                nudges.append(WellnessNudge(
                    nudge_id=f"wellness_{uuid.uuid4().hex[:8]}",
                    nudge_type="workload",
                    severity="warning",
                    title="📅 Meeting Overload",
                    message=f"You have {f.value // 60:.1f} hours of meetings today. Consider declining optional ones.",
                    suggested_action="Review meetings and identify candidates to skip or make async"
                ))
        
        write_audit("system", "wellness_agent", "generate_wellness_nudges",
                   input_refs=[user_email], output_refs=[f"nudges:{len(nudges)}"],
                   status="success")
        
        return nudges
    
    # ============================================================
    # CELEBRATION
    # ============================================================
    
    def celebrate_completion(self, task_title: str, priority: str = "P2") -> str:
        """Generate a celebration message for task completion."""
        
        celebrations = {
            "P0": [
                f"🎉 Huge win! You crushed the critical task: **{task_title}**!",
                f"🏆 P0 down! **{task_title}** is complete. That's a big deal!",
                f"⭐ Critical task conquered: **{task_title}**. You're on fire!"
            ],
            "P1": [
                f"✨ Nice work completing **{task_title}**! One less thing on your plate.",
                f"👏 **{task_title}** — done! Keep that momentum going.",
                f"💪 Great progress on **{task_title}**. You're moving forward!"
            ],
            "P2": [
                f"✅ **{task_title}** — checked off! Every completion counts.",
                f"👍 Done with **{task_title}**. Steady progress!",
                f"🙌 **{task_title}** complete. Nice work!"
            ],
            "P3": [
                f"✓ **{task_title}** completed. Good to clear the backlog!",
                f"📋 **{task_title}** — done. Every little bit helps!"
            ]
        }
        
        messages = celebrations.get(priority, celebrations["P2"])
        message = random.choice(messages)
        
        write_audit("system", "wellness_agent", "celebrate_completion",
                   input_refs=[task_title], output_refs=["celebration_sent"],
                   status="success")
        
        return message
