from __future__ import annotations
from typing import List
from agents.schemas import NudgeDraft
from agents import prompts
from governance.audit import write_audit
from governance.gateway import PolicyGateway
from repos.data_repo import DataRepo
import re
class FollowupAgent:
    def __init__(self, repo: DataRepo):
        self.repo = repo
        self.gw = PolicyGateway("followup_agent")
    
    

    def nudges(self) -> List[NudgeDraft]:
        drafts = []
        tasks_by_id = {t["task_id"]: t for t in self.repo.tasks()}

        for fu in self.repo.followups():
            t = tasks_by_id.get(fu["entity_id"], {})

            title = t.get("title", "(no title)")
            priority = t.get("priority", "NA")
            status = t.get("status", "NA")
            due_date = t.get("due_date_utc", "no due date")
            # Handle missing owner_user_id gracefully
            owner = t.get("owner_user_id") or fu.get("owner_user_id", "unknown")

            p = prompts.NUDGE_PROMPT.format(
                title=title,
                priority=priority,
                status=status,
                due_date=due_date,
                reason=fu.get("reason",""),
                channel=fu.get("recommended_channel","email"),
                owner=owner
            )
            def _strip_markdown(text: str) -> str:
                return re.sub(r"\*+", "", text)
            text = self.gw.call_llm(p, correlation_id=fu.get("correlation_id"))
            text = _strip_markdown(text.strip())
            drafts.append(NudgeDraft(
                followup_id=fu["followup_id"],
                entity_type=fu.get("entity_type", "task"),
                entity_id=fu.get("entity_id", ""),
                owner_user_id=fu.get("owner_user_id", owner),
                reason=fu.get("reason", ""),
                recommended_channel=fu.get("recommended_channel", "email"),
                draft_message=text.strip(),
                severity=fu.get("severity","low"),
                correlation_id=fu.get("correlation_id")
            ))

        write_audit("system", "followup_agent", "generate_nudge",
                    [], [d.followup_id for d in drafts], "success")

        return drafts