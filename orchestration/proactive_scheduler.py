# orchestration/proactive_scheduler.py
"""
Phase 3: Proactive Scheduler
============================
Monitors user state and triggers agents proactively without explicit requests.

Features:
- Automated morning briefings (9 AM)
- Automated EOD summaries (5 PM)
- Hourly wellness monitoring
- Deadline alerts
- Burnout prevention
- Meeting conflict detection
"""

from __future__ import annotations
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
import schedule

from repos.data_repo import DataRepo
from orchestration.super_graph import process_user_request
from orchestration.wellness_subgraph import check_wellness
from orchestration.task_subgraph import plan_tasks_for_user


# ============================================================
# PROACTIVE EVENT TYPES
# ============================================================

@dataclass
class ProactiveEvent:
    """Represents a proactive notification/action"""
    event_type: str  # briefing, alert, reminder, recommendation
    priority: str  # low, medium, high, critical
    title: str
    message: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user_email: str = ""
    requires_approval: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "priority": self.priority,
            "title": self.title,
            "message": self.message,
            "actions": self.actions,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "user_email": self.user_email,
            "requires_approval": self.requires_approval
        }


# ============================================================
# PROACTIVE MONITORS
# ============================================================

class BurnoutMonitor:
    """Monitors wellness score and alerts on burnout risk"""
    
    def __init__(self, threshold: int = 50):
        self.threshold = threshold
        self.last_check: Dict[str, datetime] = {}
        
    def check(self, user_email: str) -> Optional[ProactiveEvent]:
        """Check if user is at burnout risk"""
        try:
            result = check_wellness(user_email, trigger_source="proactive_monitor")
            score = result.get("score", 100)
            stress = result.get("stress_level", "low")
            indicators = result.get("burnout_indicators", [])
            
            if score < self.threshold:
                # High burnout risk detected
                return ProactiveEvent(
                    event_type="alert",
                    priority="high" if score < 40 else "medium",
                    title="Burnout Risk Detected",
                    message=f"Your wellness score is {score:.0f}/100 with {len(indicators)} burnout indicators. Immediate action recommended.",
                    actions=[
                        {"type": "take_break", "label": "Take 15 min break now", "duration_mins": 15},
                        {"type": "view_recommendations", "label": "View full wellness report"},
                        {"type": "notify_manager", "label": "Request manager support", "requires_approval": True}
                    ],
                    metadata={
                        "score": score,
                        "stress_level": stress,
                        "indicators_count": len(indicators),
                        "indicators": indicators[:3]  # Top 3
                    },
                    user_email=user_email,
                    requires_approval=score < 40  # Critical cases need approval
                )
                
        except Exception as e:
            print(f"[ERROR] Burnout monitor failed: {e}")
        
        return None


class DeadlineMonitor:
    """Monitors approaching deadlines and overdue tasks"""
    
    def check(self, user_email: str) -> List[ProactiveEvent]:
        """Check for deadline alerts"""
        events = []
        repo = DataRepo()
        
        try:
            tasks = repo.tasks(user_email)
            now = datetime.now()
            
            # Check for tasks due today
            due_today = [t for t in tasks 
                        if t.get("due_date") and self._is_today(t["due_date"])
                        and t.get("status") != "completed"]
            
            if due_today:
                p0_count = sum(1 for t in due_today if t.get("priority") == "P0")
                events.append(ProactiveEvent(
                    event_type="reminder",
                    priority="high" if p0_count > 0 else "medium",
                    title=f"{len(due_today)} Tasks Due Today",
                    message=f"You have {len(due_today)} tasks due today ({p0_count} critical). Review your priorities?",
                    actions=[
                        {"type": "view_tasks", "label": "View all due tasks"},
                        {"type": "plan_day", "label": "Create focus plan"}
                    ],
                    metadata={"due_today": len(due_today), "p0_count": p0_count},
                    user_email=user_email
                ))
            
            # Check for overdue tasks
            overdue = [t for t in tasks 
                      if t.get("due_date") and self._is_overdue(t["due_date"])
                      and t.get("status") != "completed"]
            
            if len(overdue) > 5:
                events.append(ProactiveEvent(
                    event_type="alert",
                    priority="high",
                    title=f"{len(overdue)} Overdue Tasks",
                    message=f"You have {len(overdue)} overdue tasks. This may be causing stress. Let's triage?",
                    actions=[
                        {"type": "triage_tasks", "label": "Auto-triage overdue items"},
                        {"type": "request_extension", "label": "Request deadline extensions"}
                    ],
                    metadata={"overdue_count": len(overdue)},
                    user_email=user_email
                ))
                
        except Exception as e:
            print(f"[ERROR] Deadline monitor failed: {e}")
        
        return events
    
    def _is_today(self, date_str: str) -> bool:
        try:
            due = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return due.date() == datetime.now().date()
        except:
            return False
    
    def _is_overdue(self, date_str: str) -> bool:
        try:
            due = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return due < datetime.now()
        except:
            return False


class WorkloadMonitor:
    """Monitors workload trends and predicts overload"""
    
    def check(self, user_email: str) -> Optional[ProactiveEvent]:
        """Check workload trends"""
        try:
            result = plan_tasks_for_user(user_email)
            plan = result.get("plan", {})
            score = plan.get("workload_score", 0)
            stress = plan.get("stress_level", "low")
            
            # Predict next week based on current trend
            # (In production, this would use historical data)
            if score >= 90:
                return ProactiveEvent(
                    event_type="recommendation",
                    priority="high",
                    title="High Workload Detected",
                    message=f"Your workload is {score:.0f}/100 (CRITICAL). Consider rescheduling or delegating tasks.",
                    actions=[
                        {"type": "delegate_tasks", "label": "Suggest delegation options"},
                        {"type": "reschedule_meetings", "label": "Reschedule low-priority meetings"},
                        {"type": "block_focus_time", "label": "Block calendar for focus"}
                    ],
                    metadata={"workload_score": score, "stress_level": stress},
                    user_email=user_email
                )
                
        except Exception as e:
            print(f"[ERROR] Workload monitor failed: {e}")
        
        return None


# ============================================================
# SCHEDULED ACTIONS
# ============================================================

class ProactiveScheduler:
    """
    Main scheduler that runs proactive monitoring and automated actions
    """
    
    def __init__(self):
        self.burnout_monitor = BurnoutMonitor(threshold=50)
        self.deadline_monitor = DeadlineMonitor()
        self.workload_monitor = WorkloadMonitor()
        self.event_queue: List[ProactiveEvent] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start the scheduler in background thread"""
        if self.running:
            print("[WARN] Scheduler already running")
            return
        
        self.running = True
        
        # Schedule automated briefings
        schedule.every().day.at("09:00").do(self._morning_briefing)
        schedule.every().day.at("17:00").do(self._eod_summary)
        
        # Schedule hourly wellness check
        schedule.every().hour.do(self._hourly_wellness_check)
        
        # Schedule deadline checks every 30 minutes
        schedule.every(30).minutes.do(self._check_deadlines)
        
        # Start background thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        print("[OK] Proactive scheduler started")
        print("  -> Morning briefing: 9:00 AM")
        print("  -> EOD summary: 5:00 PM")
        print("  -> Wellness check: Every hour")
        print("  -> Deadline check: Every 30 minutes")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        if self.thread:
            self.thread.join(timeout=2)
        print("[OK] Proactive scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    # ========================================
    # Scheduled Actions
    # ========================================
    
    def _morning_briefing(self):
        """Automated morning briefing for all active users"""
        print(f"\n[PROACTIVE] Morning Briefing - {datetime.now().strftime('%H:%M')}")
        
        # In production, loop through all active users
        users = ["kowshik.naidu@contoso.com"]
        
        for user in users:
            try:
                result = process_user_request(
                    user_input="Give me my morning briefing",
                    user_email=user
                )
                
                event = ProactiveEvent(
                    event_type="briefing",
                    priority="medium",
                    title="Good Morning! Here's Your Daily Briefing",
                    message=result.get("response", "Briefing generated"),
                    metadata={
                        "agents_used": result.get("agents_used", []),
                        "workload": result.get("task_result", {}).get("plan", {}).get("workload_score", 0)
                    },
                    user_email=user
                )
                
                self._queue_event(event)
                print(f"  -> Briefing generated for {user}")
                
            except Exception as e:
                print(f"  -> Failed for {user}: {e}")
    
    def _eod_summary(self):
        """Automated end-of-day summary"""
        print(f"\n[PROACTIVE] EOD Summary - {datetime.now().strftime('%H:%M')}")
        
        users = ["kowshik.naidu@contoso.com"]
        
        for user in users:
            try:
                result = process_user_request(
                    user_input="Give me my end-of-day report",
                    user_email=user
                )
                
                event = ProactiveEvent(
                    event_type="briefing",
                    priority="low",
                    title="End of Day Summary",
                    message=result.get("response", "Report generated"),
                    metadata={
                        "productivity_score": result.get("report_result", {}).get("productivity_score", 0)
                    },
                    user_email=user
                )
                
                self._queue_event(event)
                print(f"  -> EOD summary for {user}")
                
            except Exception as e:
                print(f"  -> Failed for {user}: {e}")
    
    def _hourly_wellness_check(self):
        """Hourly wellness monitoring"""
        print(f"\n[PROACTIVE] Wellness Check - {datetime.now().strftime('%H:%M')}")
        
        users = ["kowshik.naidu@contoso.com"]
        
        for user in users:
            event = self.burnout_monitor.check(user)
            if event:
                self._queue_event(event)
                print(f"  -> [ALERT] Burnout risk for {user}: Score {event.metadata.get('score')}/100")
            else:
                print(f"  -> {user} wellness OK")
    
    def _check_deadlines(self):
        """Check for approaching/overdue deadlines"""
        print(f"\n[PROACTIVE] Deadline Check - {datetime.now().strftime('%H:%M')}")
        
        users = ["kowshik.naidu@contoso.com"]
        
        for user in users:
            events = self.deadline_monitor.check(user)
            for event in events:
                self._queue_event(event)
                print(f"  -> [ALERT] {event.title} for {user}")
            
            if not events:
                print(f"  -> {user} deadlines OK")
    
    # ========================================
    # Event Management
    # ========================================
    
    def _queue_event(self, event: ProactiveEvent):
        """Add event to queue for UI to display"""
        self.event_queue.append(event)
        
        # Keep only last 50 events
        if len(self.event_queue) > 50:
            self.event_queue = self.event_queue[-50:]
    
    def get_pending_events(self, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending events for a user"""
        if user_email:
            events = [e for e in self.event_queue if e.user_email == user_email]
        else:
            events = self.event_queue
        
        return [e.to_dict() for e in events]
    
    def clear_event(self, timestamp: str):
        """Clear/dismiss an event"""
        self.event_queue = [e for e in self.event_queue if e.timestamp != timestamp]
    
    def trigger_manual_check(self, user_email: str) -> List[ProactiveEvent]:
        """Manually trigger all monitors for a user"""
        events = []
        
        # Burnout check
        burnout_event = self.burnout_monitor.check(user_email)
        if burnout_event:
            events.append(burnout_event)
        
        # Deadline checks
        deadline_events = self.deadline_monitor.check(user_email)
        events.extend(deadline_events)
        
        # Workload check
        workload_event = self.workload_monitor.check(user_email)
        if workload_event:
            events.append(workload_event)
        
        return events


# ============================================================
# GLOBAL SCHEDULER INSTANCE
# ============================================================

_scheduler_instance: Optional[ProactiveScheduler] = None

def get_scheduler() -> ProactiveScheduler:
    """Get or create global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ProactiveScheduler()
    return _scheduler_instance


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def start_proactive_monitoring():
    """Start the proactive scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_proactive_monitoring():
    """Stop the proactive scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()


def get_user_notifications(user_email: str) -> List[Dict[str, Any]]:
    """Get all pending notifications for a user"""
    scheduler = get_scheduler()
    return scheduler.get_pending_events(user_email)


def run_manual_check(user_email: str) -> List[Dict[str, Any]]:
    """Manually trigger all proactive checks for a user"""
    scheduler = get_scheduler()
    events = scheduler.trigger_manual_check(user_email)
    
    # Queue events
    for event in events:
        scheduler._queue_event(event)
    
    return [e.to_dict() for e in events]


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    print("="*70)
    print("  Phase 3: Proactive Scheduler Demo")
    print("="*70)
    
    # Start scheduler
    scheduler = start_proactive_monitoring()
    
    print("\n[INFO] Scheduler running in background...")
    print("[INFO] In production, this runs 24/7 monitoring all users")
    print("\n[DEMO] Running manual checks now instead of waiting...")
    
    # Run manual checks to demonstrate
    user = "kowshik.naidu@contoso.com"
    
    print(f"\n--- Manual Check for {user} ---")
    events = run_manual_check(user)
    
    if events:
        print(f"\n[OK] Found {len(events)} proactive events:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. [{event['priority'].upper()}] {event['title']}")
            print(f"   {event['message']}")
            print(f"   Actions:")
            for action in event['actions']:
                print(f"     - {action['label']}")
            print()
    else:
        print("\n[OK] No alerts - user is in good state!")
    
    print("\n[INFO] Scheduler will continue running...")
    print("[INFO] Morning briefing at 9:00 AM, EOD at 5:00 PM")
    print("[INFO] Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(10)
            # Show any new events
            new_events = scheduler.get_pending_events(user)
            if new_events:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(new_events)} notifications pending")
    except KeyboardInterrupt:
        print("\n\n[INFO] Stopping scheduler...")
        stop_proactive_monitoring()
        print("[OK] Demo complete!")
