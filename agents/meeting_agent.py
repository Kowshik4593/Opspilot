from __future__ import annotations
from typing import Dict, Any, List
import json, re
from agents.schemas import MoM
from agents import prompts
from repos.data_repo import DataRepo
from governance.gateway import PolicyGateway
from governance.audit import write_audit

SECTION_PREFIXES = (
    "summary:", "decision:", "decisions:",
    "action:", "actions:", "action item:", "action items:",
    "risk:", "risks:",
    "dependency:", "dependencies:"
)

def _strip_prefix(s: str) -> str:
    s0 = s.strip().lstrip("-•").strip()
    s1 = s0
    low = s0.lower()
    for p in SECTION_PREFIXES:
        if low.startswith(p):
            s1 = s0[len(p):].strip()
            break
    return s1

def _heuristic_parse(text: str) -> Dict[str, Any]:
    """Fallback parsing when JSON is not returned."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    summary = ""
    decisions: List[str] = []
    actions: List[str] = []
    risks: List[str] = []
    deps: List[str] = []

    # Try to identify blocks by keyword
    for ln in lines:
        ln_clean = _strip_prefix(ln)
        l = ln.lower()
        if not summary and ("summary" in l or ("decision" not in l and "action" not in l and "risk" not in l and len(ln_clean.split()) > 3)):
            # First decent sentence becomes summary
            summary = ln_clean if ln_clean else ln
            continue

        if "decision" in l:
            decisions.append(ln_clean or ln)
        elif "action" in l:
            actions.append(ln_clean or ln)
        elif "risk" in l:
            risks.append(ln_clean or ln)
        elif "dependenc" in l:
            deps.append(ln_clean or ln)

    if not summary and lines:
        summary = _strip_prefix(lines[0])[:400]

    # Deduplicate and drop obviously wrong “prefixed leftovers”
    def clean_list(arr: List[str]) -> List[str]:
        out = []
        seen = set()
        for a in arr:
            a2 = _strip_prefix(a)
            if not a2: continue
            a2 = re.sub(r'^\W+', '', a2).strip()
            if a2 and a2.lower() not in seen:
                seen.add(a2.lower())
                out.append(a2)
        return out

    return {
        "summary": summary[:400] if summary else "Summary not available.",
        "decisions": clean_list(decisions),
        "action_items": clean_list(actions),
        "risks": clean_list(risks),
        "dependencies": clean_list(deps),
    }

class MeetingAgent:
    def __init__(self, repo: DataRepo):
        self.repo = repo
        self.gw = PolicyGateway("meeting_agent")

    def generate_mom(self, meeting_id: str) -> MoM:
        mtg = next(m for m in self.repo.meetings() if m["meeting_id"] == meeting_id)
        transcript = self.repo.get_transcript(mtg.get("transcript_file"))
        if not transcript.strip():
            transcript = (
                f"[No transcript available]\n"
                f"Meeting: {mtg.get('title','')}\n"
                f"Participants: {', '.join(mtg.get('participant_emails', []))}"
            )

        text = self.gw.call_llm(
            prompts.MOM_PROMPT.format(transcript=transcript[:7000]),
            correlation_id=mtg.get("correlation_id")
        ).strip()

        # 1) Try strict JSON parse
        parsed = None
        if text and text.startswith("{"):
            try:
                obj = json.loads(text)
                parsed = {
                    "summary": obj.get("summary") or "Summary not available.",
                    "decisions": obj.get("decisions") or [],
                    "action_items": obj.get("action_items") or [],
                    "risks": obj.get("risks") or [],
                    "dependencies": obj.get("dependencies") or [],
                }
            except Exception:
                parsed = None

        # 2) Fallback to heuristic parsing
        if not parsed:
            parsed = _heuristic_parse(text)

        # Compare to existing MoM (either from calendar/mom.json or per-file loader)
        existing = next((x for x in self.repo.mom_entries() if x.get("meeting_id")==meeting_id), None)
        delta = None
        if existing:
            exist_actions = [a.strip() for a in existing.get("action_items", []) if a and isinstance(a, str)]
            new_actions = [a.strip() for a in parsed["action_items"] if a and isinstance(a, str)]
            delta = f"+{len(set(new_actions)-set(exist_actions))} new actions; " \
                    f"-{len(set(exist_actions)-set(new_actions))} missing vs existing"

        res = MoM(
            meeting_id=meeting_id,
            summary=(parsed["summary"] or "Summary not available.")[:400],
            decisions=parsed["decisions"],
            action_items=parsed["action_items"],
            risks=parsed["risks"],
            dependencies=parsed["dependencies"],
            correlation_id=mtg.get("correlation_id"),
            delta_vs_existing=delta
        )
        write_audit("system", "meeting_agent", "generate_mom",
                    [meeting_id], [f"{meeting_id}:mom"], "success", mtg.get("correlation_id"))
        return res