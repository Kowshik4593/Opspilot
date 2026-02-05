from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timedelta
from agents.schemas import Narrative
from agents import prompts
from repos.data_repo import DataRepo
from governance.gateway import PolicyGateway
from governance.audit import write_audit

class ReportingAgent:
    def __init__(self, repo: DataRepo):
        self.repo = repo
        self.gw = PolicyGateway("reporting_agent")

    def _get_task_details(self, task_id: str) -> Dict[str, Any]:
        """Get full task details by ID"""
        tasks = self.repo.tasks()
        for t in tasks:
            if t.get("task_id") == task_id:
                return t
        return {"task_id": task_id, "title": task_id, "priority": "P3"}

    def _get_email_details(self, email_id: str) -> Dict[str, Any]:
        """Get email details by ID"""
        emails = self.repo.inbox()
        for e in emails:
            if e.get("email_id") == email_id:
                return e
        return {"email_id": email_id, "subject": email_id}

    def _calculate_productivity_score(self, e: dict) -> int:
        """Calculate productivity score based on task completion"""
        completed = len(e.get("tasks_completed", []))
        in_progress = len(e.get("tasks_in_progress", []))
        pending = len(e.get("tasks_pending", []))
        risks = len(e.get("risks_flagged", []))
        
        total = completed + in_progress + pending
        if total == 0:
            return 50
        
        # Base score from completion rate
        score = int((completed / total) * 100)
        
        # Bonus for progress
        score += min(in_progress * 5, 20)
        
        # Penalty for risks
        score -= risks * 10
        
        return max(0, min(100, score))

    def _get_priority_breakdown(self, task_ids: List[str]) -> Dict[str, int]:
        """Get count of tasks by priority"""
        breakdown = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for tid in task_ids:
            task = self._get_task_details(tid)
            priority = task.get("priority", "P3")
            if priority in breakdown:
                breakdown[priority] += 1
        return breakdown

    def format_eod_pretty(self, e: dict, narrative: str) -> str:
        """Build a comprehensive, detailed EOD report"""
        lines = []
        
        # Header with date and productivity score
        prod_score = self._calculate_productivity_score(e)
        score_emoji = "🟢" if prod_score >= 70 else "🟡" if prod_score >= 50 else "🔴"
        
        lines.append("# 📊 End of Day Report")
        lines.append("")
        lines.append(f"**📅 Date:** {e.get('date', datetime.now().strftime('%Y-%m-%d'))}")
        lines.append(f"**👤 User:** {e.get('user_id', 'Unknown')}")
        lines.append(f"**{score_emoji} Productivity Score:** {prod_score}/100")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Executive Summary
        lines.append("## 📝 Executive Summary")
        lines.append("")
        lines.append(narrative.strip() or "No summary available.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Task Statistics
        completed = e.get("tasks_completed", [])
        inprog = e.get("tasks_in_progress", [])
        pending = e.get("tasks_pending", [])
        total_tasks = len(completed) + len(inprog) + len(pending)
        
        lines.append("## 📈 Daily Statistics")
        lines.append("")
        lines.append(f"| Metric | Count | Percentage |")
        lines.append(f"|--------|-------|------------|")
        lines.append(f"| ✅ Completed | {len(completed)} | {int(len(completed)/total_tasks*100) if total_tasks else 0}% |")
        lines.append(f"| 🔄 In Progress | {len(inprog)} | {int(len(inprog)/total_tasks*100) if total_tasks else 0}% |")
        lines.append(f"| ⏳ Pending | {len(pending)} | {int(len(pending)/total_tasks*100) if total_tasks else 0}% |")
        lines.append(f"| **Total** | **{total_tasks}** | **100%** |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Completed Tasks with Details
        lines.append("## ✅ Completed Tasks")
        lines.append("")
        if completed:
            for tid in completed:
                task = self._get_task_details(tid)
                title = task.get("title", tid)
                priority = task.get("priority", "P3")
                tags = task.get("tags", [])
                priority_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(priority, "⚪")
                
                lines.append(f"### {priority_emoji} [{priority}] {title}")
                if task.get("description"):
                    lines.append(f"> {task.get('description', '')[:150]}...")
                if tags:
                    lines.append(f"**Tags:** {', '.join(tags)}")
                lines.append("")
        else:
            lines.append("*No tasks completed today.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # In Progress with Details
        lines.append("## 🔄 In Progress")
        lines.append("")
        if inprog:
            priority_breakdown = self._get_priority_breakdown(inprog)
            lines.append(f"**Priority Breakdown:** 🔴 P0: {priority_breakdown['P0']} | 🟠 P1: {priority_breakdown['P1']} | 🟡 P2: {priority_breakdown['P2']} | 🟢 P3: {priority_breakdown['P3']}")
            lines.append("")
            
            for tid in inprog:
                task = self._get_task_details(tid)
                title = task.get("title", tid)
                priority = task.get("priority", "P3")
                due = task.get("due_date_utc", "No due date")[:10] if task.get("due_date_utc") else "No due date"
                priority_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(priority, "⚪")
                
                lines.append(f"- {priority_emoji} **[{priority}]** {title} *(Due: {due})*")
        else:
            lines.append("*No tasks in progress.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Pending Tasks
        lines.append("## ⏳ Pending Tasks")
        lines.append("")
        if pending:
            priority_breakdown = self._get_priority_breakdown(pending)
            lines.append(f"**Priority Breakdown:** 🔴 P0: {priority_breakdown['P0']} | 🟠 P1: {priority_breakdown['P1']} | 🟡 P2: {priority_breakdown['P2']} | 🟢 P3: {priority_breakdown['P3']}")
            lines.append("")
            
            for tid in pending:
                task = self._get_task_details(tid)
                title = task.get("title", tid)
                priority = task.get("priority", "P3")
                priority_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(priority, "⚪")
                
                lines.append(f"- {priority_emoji} **[{priority}]** {title}")
        else:
            lines.append("*No pending tasks.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Follow-ups
        fus = e.get("followups_triggered", [])
        lines.append("## 🔔 Follow-ups & Reminders")
        lines.append("")
        if fus:
            for f in fus:
                lines.append(f"- ⏰ {f}")
        else:
            lines.append("*No follow-ups triggered today.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Risks
        risks = e.get("risks_flagged", [])
        lines.append("## ⚠️ Risks & Blockers")
        lines.append("")
        if risks:
            lines.append(f"**{len(risks)} risk(s) identified:**")
            lines.append("")
            for r in risks:
                task = self._get_task_details(r)
                title = task.get("title", r)
                lines.append(f"- 🚨 **{title}**")
                if task.get("description"):
                    lines.append(f"  - Impact: {task.get('description', '')[:100]}...")
        else:
            lines.append("✅ *No risks flagged today.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Tomorrow's Focus
        lines.append("## 🎯 Tomorrow's Focus")
        lines.append("")
        # Get P0 and P1 tasks from pending and in_progress
        high_priority = []
        for tid in inprog + pending:
            task = self._get_task_details(tid)
            if task.get("priority") in ["P0", "P1"]:
                high_priority.append(task)
        
        if high_priority:
            lines.append("**High Priority Items to Address:**")
            for task in high_priority[:5]:
                lines.append(f"1. {task.get('title', 'Unknown task')}")
        else:
            lines.append("*No critical items pending. Good job!*")
        lines.append("")

        return "\n".join(lines)

    def eod(self) -> List[Narrative]:
        out = []
        for e in self.repo.eod():
            # If ground truth exists, use it; else generate
            nar = e.get("narrative_gt")
            if not nar:
                nar = self.gw.call_llm(
                    prompts.EOD_PROMPT.format(
                        completed=e.get("tasks_completed", []),
                        in_progress=e.get("tasks_in_progress", []),
                        pending=e.get("tasks_pending", []),
                        followups=e.get("followups_triggered", []),
                    )
                )

            pretty = self.format_eod_pretty(e, nar)
            out.append(Narrative(kind="eod", narrative=pretty, correlation_ids=e.get("correlation_ids", [])))

        write_audit("system", "reporting_agent", "generate_eod", [], [], "success")
        return out

    def format_weekly_pretty(self, w: dict, narrative: str) -> str:
        """Build a comprehensive weekly summary report"""
        lines = []
        
        # Header
        lines.append("# 📊 Weekly Summary Report")
        lines.append("")
        lines.append(f"**📅 Week:** {w.get('week_id', 'Unknown')}")
        lines.append(f"**👥 Team:** {w.get('team_id', 'Unknown')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Executive Summary
        lines.append("## 📝 Executive Summary")
        lines.append("")
        exec_summary = w.get("exec_summary_gt", narrative)
        lines.append(exec_summary.strip() if exec_summary else "No summary available.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Velocity Metrics
        metrics = w.get("velocity_metrics", {})
        # Initialize carryover outside the if block so it's always defined
        carryover = metrics.get("carryover", 0) if metrics else 0
        
        if metrics:
            lines.append("## 📈 Velocity Metrics")
            lines.append("")
            
            story_points = metrics.get("story_points_completed", 0)
            defects = metrics.get("defects", 0)
            
            # Calculate velocity health
            if carryover == 0:
                health = "🟢 Excellent"
            elif carryover <= story_points * 0.2:
                health = "🟡 Good"
            else:
                health = "🔴 Needs Attention"
            
            lines.append(f"| Metric | Value | Status |")
            lines.append(f"|--------|-------|--------|")
            lines.append(f"| Story Points Completed | {story_points} | ✅ |")
            lines.append(f"| Carryover | {carryover} | {'⚠️' if carryover > 0 else '✅'} |")
            lines.append(f"| Defects | {defects} | {'⚠️' if defects > 2 else '✅'} |")
            lines.append(f"| **Sprint Health** | - | **{health}** |")
            lines.append("")
            
            # Completion rate
            total_planned = story_points + carryover
            completion_rate = int((story_points / total_planned) * 100) if total_planned > 0 else 100
            lines.append(f"**Completion Rate:** {completion_rate}%")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Milestones
        milestones = w.get("milestones_achieved", [])
        lines.append("## 🏆 Milestones Achieved")
        lines.append("")
        if milestones:
            for m in milestones:
                lines.append(f"- ✅ **{m}**")
        else:
            lines.append("*No milestones achieved this week.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Risks
        risks = w.get("top_risks", [])
        lines.append("## ⚠️ Top Risks")
        lines.append("")
        if risks:
            lines.append(f"**{len(risks)} risk(s) being tracked:**")
            lines.append("")
            for i, risk in enumerate(risks, 1):
                risk_text = risk.get("risk", risk) if isinstance(risk, dict) else risk
                owner = risk.get("owner_email", "Unassigned") if isinstance(risk, dict) else "Unassigned"
                mitigation = risk.get("mitigation", "No mitigation plan") if isinstance(risk, dict) else "No mitigation plan"
                
                lines.append(f"### Risk #{i}: {risk_text}")
                lines.append(f"- **Owner:** {owner}")
                lines.append(f"- **Mitigation:** {mitigation}")
                lines.append("")
        else:
            lines.append("✅ *No significant risks this week.*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Weekly highlights from emails and tasks
        lines.append("## 📬 Activity Summary")
        lines.append("")
        
        # Get email count for the week
        emails = self.repo.inbox()
        processed = len([e for e in emails if e.get("processed", False)])
        actionable = len([e for e in emails if e.get("actionability_gt") == "actionable"])
        
        lines.append(f"| Activity | Count |")
        lines.append(f"|----------|-------|")
        lines.append(f"| Emails Processed | {processed} |")
        lines.append(f"| Actionable Items | {actionable} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Next Week Focus
        lines.append("## 🎯 Next Week Focus")
        lines.append("")
        if risks:
            lines.append("**Priority Items:**")
            for risk in risks[:3]:
                risk_text = risk.get("risk", risk) if isinstance(risk, dict) else risk
                lines.append(f"1. Address: {risk_text}")
        
        if carryover > 0:
            lines.append(f"2. Complete {carryover} carryover items")
        
        lines.append("")

        return "\n".join(lines)

    def weekly(self) -> List[Narrative]:
        outs = []
        for w in self.repo.weekly():
            nar = w.get("narrative_gt") or w.get("exec_summary_gt") or self.gw.call_llm("Give weekly summary in 3-5 bullets.")
            pretty = self.format_weekly_pretty(w, nar)
            outs.append(Narrative(kind="weekly", narrative=pretty, correlation_ids=w.get("correlation_ids", [])))

        write_audit("system", "reporting_agent", "generate_weekly", [], [], "success")
        return outs
    
    def generate_comprehensive_eod(self, user_email: str = None) -> str:
        """Generate a comprehensive EOD report with real-time data"""
        lines = []
        
        # Get current data
        tasks = self.repo.tasks()
        emails = self.repo.inbox()
        meetings = self.repo.meetings()
        
        # Filter by user if provided
        if user_email:
            user = self.repo.user_by_email(user_email)
            user_id = user.get("user_id") if user else None
        else:
            user_id = None
        
        # Calculate stats
        today = datetime.now().strftime("%Y-%m-%d")
        
        completed = [t for t in tasks if t.get("status") in ["done", "completed"]]
        in_progress = [t for t in tasks if t.get("status") == "in_progress"]
        pending = [t for t in tasks if t.get("status") == "todo"]
        
        p0_tasks = [t for t in tasks if t.get("priority") == "P0"]
        overdue = [t for t in tasks if t.get("due_date_utc") and t.get("due_date_utc")[:10] < today and t.get("status") not in ["done", "completed"]]
        
        processed_emails = [e for e in emails if e.get("processed", False)]
        actionable_emails = [e for e in emails if e.get("actionability_gt") == "actionable"]
        
        # Build report
        lines.append("# 📊 Comprehensive End of Day Report")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Task Overview
        lines.append("## 📋 Task Overview")
        lines.append("")
        lines.append(f"| Status | Count |")
        lines.append(f"|--------|-------|")
        lines.append(f"| ✅ Completed | {len(completed)} |")
        lines.append(f"| 🔄 In Progress | {len(in_progress)} |")
        lines.append(f"| ⏳ Pending | {len(pending)} |")
        lines.append(f"| 🔴 Critical (P0) | {len(p0_tasks)} |")
        lines.append(f"| ⚠️ Overdue | {len(overdue)} |")
        lines.append("")
        
        # Critical items
        if p0_tasks:
            lines.append("### 🚨 Critical Tasks (P0)")
            for t in p0_tasks:
                status_emoji = "✅" if t.get("status") in ["done", "completed"] else "🔄" if t.get("status") == "in_progress" else "⏳"
                lines.append(f"- {status_emoji} {t.get('title', 'Unknown')}")
            lines.append("")
        
        # Overdue items
        if overdue:
            lines.append("### ⚠️ Overdue Tasks")
            for t in overdue:
                lines.append(f"- 🔴 {t.get('title', 'Unknown')} (Due: {t.get('due_date_utc', '')[:10]})")
            lines.append("")
        
        # Email summary
        lines.append("## 📧 Email Summary")
        lines.append("")
        lines.append(f"- **Total Processed:** {len(processed_emails)}")
        lines.append(f"- **Actionable:** {len(actionable_emails)}")
        lines.append(f"- **Pending Action:** {len([e for e in actionable_emails if not e.get('processed')])}")
        lines.append("")
        
        # Meeting summary
        lines.append("## 📅 Meetings")
        lines.append("")
        today_meetings = [m for m in meetings if m.get("start_utc", "")[:10] == today]
        lines.append(f"**Today's Meetings:** {len(today_meetings)}")
        for m in today_meetings[:5]:
            lines.append(f"- {m.get('title', 'Unknown meeting')}")
        lines.append("")
        
        return "\n".join(lines)