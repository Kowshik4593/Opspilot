from __future__ import annotations
from typing import List, Dict, Any, Set
from agents.schemas import TodayPlan, TaskPlanBlock
from governance.audit import write_audit
from governance.gateway import PolicyGateway
from repos.data_repo import DataRepo

class TasksAgent:
    def __init__(self, repo: DataRepo):
        self.repo = repo
        self.gw = PolicyGateway("tasks_agent")

    def _eisenhower(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        board = {"P0": [], "P1": [], "P2": [], "P3": []}
        for t in tasks:
            pr = t.get("priority", "P2")
            board.setdefault(pr, []).append(t)
        # sort by due_date if present (soonest first)
        def dd(x):
            return x.get("due_date_utc") or "9999-12-31T23:59:59+00:00"
        for k in board:
            board[k].sort(key=dd)
        return board

    def _user_ids_for_email(self, user_email: str) -> Set[str]:
        # Find all users with this email (usually one)
        users = [u for u in self.repo.users() if u.get("email") == user_email]
        return {u["user_id"] for u in users}

    def _tasks_for_user(self, user_email: str) -> List[Dict[str, Any]]:
        owner_ids = self._user_ids_for_email(user_email)
        if not owner_ids:
            return []

        tasks = self.repo.tasks()
        mine = [t for t in tasks if t.get("owner_user_id") in owner_ids]

        # If empty, try a permissive fallback: tasks that mention the user's email in description/title (optional)
        if not mine:
            lowered = user_email.lower()
            mine = [
                t for t in tasks
                if lowered in (t.get("description","") + " " + t.get("title","")).lower()
            ]
        return mine

    def plan_today(self, user_email: str) -> TodayPlan:
        user_tasks = self._tasks_for_user(user_email)

        # Build board and choose up to 3 focus blocks with P0>P1>P2>P3 priority
        board = self._eisenhower(user_tasks)
        focus: List[TaskPlanBlock] = []

        def add_blocks(pri: str, limit: int = 3):
            for t in board.get(pri, []):
                if len(focus) >= limit:
                    break
                dur = t.get("estimated_duration_minutes")
                if dur is None:
                    # simple inference: tighter priorities get more time
                    dur = 60 if pri in ("P0","P1") else 30
                focus.append(TaskPlanBlock(title=t["title"], duration_minutes=int(dur)))

        for lane in ["P0", "P1", "P2", "P3"]:
            add_blocks(lane, limit=3)
            if len(focus) >= 3:
                break

        # Craft a more informative narrative even in simulation mode
        total = len(user_tasks)
        p0 = len(board.get("P0", []))
        p1 = len(board.get("P1", []))
        p2 = len(board.get("P2", []))
        p3 = len(board.get("P3", []))
        # Ask LLM (or sim) to produce a succinct narrative with the stats
        narrative_prompt = (
    "Create a concise 'Today's Plan' for {user_email}:\n"
    f"- Total tasks: {total}; P0: {p0}, P1: {p1}, P2: {p2}, P3: {p3}.\n"
    "- Prioritize P0/P1. Propose 2–3 focus blocks with short rationale (1 sentence each). "
    "Mention any due-today or overdue items explicitly."
)

        narrative = self.gw.call_llm(narrative_prompt, correlation_id=None)

        write_audit("system", "tasks_agent", "schedule_plan",
                    input_refs=[],
                    output_refs=[f"focus_blocks={len(focus)}", f"tasks={total}"],
                    status="success")
        return TodayPlan(user_email=user_email, narrative=narrative.strip(), focus_blocks=focus)