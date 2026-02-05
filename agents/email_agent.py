
from __future__ import annotations
from typing import Dict, Any, List
from agents.schemas import EmailTriageResult, ExtractedAction
from agents import prompts
from repos.data_repo import DataRepo
from governance.gateway import PolicyGateway
from governance.audit import write_audit

class EmailAgent:
    def __init__(self, repo: DataRepo):
        self.repo = repo
        self.gw = PolicyGateway("email_agent")

    def _summarize(self, email: Dict[str, Any]) -> str:
        p = prompts.EMAIL_SUMMARY_PROMPT.format(subject=email["subject"], body=email["body_text"])
        return self.gw.call_llm(p, correlation_id=email.get("correlation_id"))

    def _extract_actions(self, email: Dict[str, Any]) -> List[ExtractedAction]:
        # For Phase-1, try LLM; fallback to trivial heuristic (look for "by <date>" patterns)
        p = prompts.EMAIL_ACTIONS_PROMPT.format(subject=email["subject"], body=email["body_text"])
        text = self.gw.call_llm(p, correlation_id=email.get("correlation_id"))
        # Lenient parse (LLM-simulated path returns plain text) -> keep empty list on failure
        try:
            import json
            raw = json.loads(text) if text.strip().startswith("[") else []
            return [ExtractedAction(**it, source_ref_id=email["email_id"]) for it in raw]
        except Exception:
            return []

    def _draft_reply(self, email: Dict[str, Any], user_ctx: Dict[str, Any]) -> str:
        p = prompts.EMAIL_REPLY_PROMPT.format(
            tone=user_ctx.get("communication_tone","neutral"),
            from_email=email["from_email"],
            subject=email["subject"],
            body=email["body_text"],
            signature=f"{user_ctx.get('display_name','')} \n{user_ctx.get('title','')}"
        )
        return self.gw.call_llm(p, correlation_id=email.get("correlation_id"))

    def analyze_actionability(self, email: Dict[str, Any]) -> str:
        """Analyze email actionability and return classification."""
        actionability = email.get("actionability_gt", "informational")
        return actionability

    def run(self, email_id: str, user_email: str) -> EmailTriageResult:
        email = next(e for e in self.repo.inbox() if e["email_id"] == email_id)
        user = self.repo.user_by_email(user_email) or {}

        write_audit("system", "email_agent", "classify_email",
                    input_refs=[email_id], output_refs=[email.get("actionability_gt","")],
                    status="success", correlation_id=email.get("correlation_id"))

        summary = self._summarize(email)
        actions = self._extract_actions(email)

        reply = self._draft_reply(email, user)

        res = EmailTriageResult(
            email_id=email["email_id"],
            triage_class=email.get("actionability_gt","informational"),
            summary=summary.strip(),
            actions=actions,
            reply_draft=reply.strip(),
            correlation_id=email.get("correlation_id")
        )

        write_audit("system", "email_agent", "draft_reply",
                    input_refs=[email_id], output_refs=[email_id+":reply"],
                    status="success", correlation_id=email.get("correlation_id"))
        return res
