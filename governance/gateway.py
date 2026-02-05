
from __future__ import annotations
import re, time, json
from typing import Dict, Any, Optional, Tuple
from config.settings import SETTINGS
from governance.usage import write_usage

# Import enhanced gateway
try:
    from governance.litellm_gateway import EnhancedLiteLLMGateway
    _enhanced_gateway_available = True
except ImportError:
    _enhanced_gateway_available = False

# OpenAI client for LiteLLM proxy (legacy fallback)
try:
    from openai import OpenAI
    _openai_available = True
except Exception:
    _openai_available = False

# Load policies once
POLICIES = json.loads(SETTINGS["governance"]["policies_file"].read_text())
DAILY_BUDGET_DEFAULT = SETTINGS["governance"]["daily_budget_usd"]

def _redact(text: str) -> str:
    masks = POLICIES.get("pii_redaction_regex", {})
    for _, pattern in masks.items():
        text = re.sub(pattern, "[REDACTED]", text)
    return text

class PolicyGateway:
    """
    Policy Gateway (Legacy)
    
    NOTE: For new code, use EnhancedLiteLLMGateway from governance.litellm_gateway
    This is kept for backward compatibility.
    """
    def __init__(self, agent_name: str):
        self.agent = agent_name
        self.model = SETTINGS["models"]["chat_model"]
        
        # Try to use enhanced gateway if available
        if _enhanced_gateway_available:
            self._enhanced = EnhancedLiteLLMGateway(agent_name, enable_cache=True)
        else:
            self._enhanced = None

    def check_budget(self) -> Tuple[bool, float]:
        # NOTE: In Phase-1 we simulate budget tracking via write_usage totals (not implemented fully)
        # Always allow but return remaining as default for demo
        agent_budget = POLICIES.get("daily_budgets", {}).get(f"{self.agent}_usd", DAILY_BUDGET_DEFAULT)
        return True, agent_budget

    def call_llm(self, prompt: str, temperature: float = 0.2,
                    max_tokens: int = 1024, correlation_id: Optional[str] = None) -> str:
            """
            Call LLM with policy enforcement
            
            This method now delegates to EnhancedLiteLLMGateway if available,
            which provides caching, retry logic, and better error handling.
            """
            import time
            start = time.time()
            
            # Use enhanced gateway if available
            if self._enhanced:
                try:
                    return self._enhanced.call(
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        correlation_id=correlation_id,
                        use_cache=True
                    )
                except Exception as e:
                    # Fallback to legacy implementation
                    print(f"⚠️  Enhanced gateway failed, falling back to legacy: {e}")
            
            ok, remaining = self.check_budget()
            if not ok:
                write_usage(self.agent, self.model, 0, 0, 0, 0.0, "fail", rate_limited=True, correlation_id=correlation_id)
                raise RuntimeError(f"Budget exceeded for {self.agent}")

            # IMPORTANT: Redact only for LOGGING, not for the prompt used in deterministic fallback
            safe_prompt_for_logging = _redact(prompt)

            # ---- Simulation mode (no API key or openai not installed) ----
            if not _openai_available or not SETTINGS["models"]["azure_api_key"]:
                # Generate a deterministic but proper output depending on agent
                out = self._simulate_response(prompt)
                # Log usage (simulated)
                write_usage(self.agent, self.model, len(prompt)//4, len(out)//4,
                            int((time.time()-start)*1000), 0.0, "success", correlation_id=correlation_id,
                            meta={"simulated": True})
                return out

            # ---- Real LLM call via OpenAI client to LiteLLM proxy ----
            # The proxy expects the full model name (e.g., azure/sc-rnd-gpt-4o-mini-01)
            try:
                client = OpenAI(
                    base_url=SETTINGS["models"]["azure_api_base"],
                    api_key=SETTINGS["models"]["azure_api_key"]
                )
                resp = client.chat.completions.create(
                    model=self.model,  # e.g., "azure/sc-rnd-gpt-4o-mini-01"
                    messages=[
                        {"role": "system", "content": f"You are the {self.agent} with enterprise guardrails."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30.0
                )
                text = resp.choices[0].message.content
                usage = resp.usage
                tokens_in = usage.prompt_tokens if usage else 0
                tokens_out = usage.completion_tokens if usage else 0
                latency = int((time.time() - start) * 1000)
                write_usage(self.agent, self.model, tokens_in, tokens_out, latency, 0.0, "success",
                            correlation_id=correlation_id,
                            meta={"prompt_redacted_for_logs": bool(safe_prompt_for_logging != prompt)})
                return text
            except Exception as e:
                write_usage(self.agent, self.model, 0, 0, int((time.time()-start)*1000), 0.0, "fail",
                            correlation_id=correlation_id, meta={"error": str(e)})
                raise

        # Add this helper method inside PolicyGateway class:
    def _simulate_response(self, prompt: str) -> str:
        """
        Deterministic, template-based responses for Phase-1 demo when no Azure key is configured.
        Produces clean outputs instead of echoing the prompt.
        """
            # Email agent templates
        if self.agent == "email_agent":
                # Heuristics: if the prompt includes 'Write a concise, professional reply' -> return a real reply
            if "Write a concise, professional reply" in prompt:
                return (
                        "Hi team,\n\n"
                        "Thanks for the update on the quarterly noise reduction initiative. I acknowledge the plan for regular checks "
                        "and the awareness campaign. I’ll participate and ensure my area follows the guidelines.\n\n"
                        "Next steps:\n"
                        "• Note the schedule for noise checks\n"
                        "• Share the awareness materials with the team\n"
                        "• Raise any issues to the supervisor as needed\n\n"
                        "Best regards,\n"
                        "Kowshik Naidu\n"
                        "SmartOps Engineer"
                    )
            if "Summarize the email" in prompt:
                return ("Summary: The manager announces a quarterly noise reduction initiative with regular checks and an "
                            "awareness campaign; team cooperation is requested and queries should go to supervisors.")
            if "From the email, extract explicit action items" in prompt:
                    # Nothing actionable in this ‘noise’ example
                return "[]"

            # Meeting agent templates
        if self.agent == "meeting_agent":
            # Parse transcript to generate dynamic MoM
            return self._generate_dynamic_mom(prompt)

            # Tasks/Followup/Reporting simple defaults
        if self.agent == "tasks_agent":
            return "Focus on P0/P1 items first; allocate 2–3 focused blocks. Communicate blockers early."
        if self.agent == "followup_agent":
            import re

            def extract(field):
                m = re.search(fr"{field}:(.*)", prompt)
                return (m.group(1).strip() if m else "")

            title = extract("Task Title")
            due_date = extract("Due Date")
            status = extract("Status")
            priority = extract("Priority")

            return (
                f"Quick reminder about {title}. "
                f"It is currently {status}, with a priority of {priority}, "
                f"and the due date is {due_date}. "
                f"Could you share a short update or let me know if anything is blocking progress?"
            )
        if self.agent == "reporting_agent":
            return "Completed: 1; In progress: 1; Pending: 1. Risks noted; follow-ups initiated."

        # Chat router - intent classification
        if self.agent == "chat_router":
            # Parse the intent classification request
            import json
            prompt_lower = prompt.lower()
            
            # Default intent detection based on keywords
            if any(kw in prompt_lower for kw in ['p0', 'p1', 'p2', 'task', 'todo', 'overdue', 'my tasks']):
                return json.dumps({
                    "intent": "tasks.list",
                    "confidence": 0.95,
                    "slots": {"priority": "P0" if "p0" in prompt_lower else None},
                    "reasoning": "Detected task-related keywords"
                })
            elif any(kw in prompt_lower for kw in ['email', 'inbox', 'unread', 'mail']):
                return json.dumps({
                    "intent": "emails.list",
                    "confidence": 0.9,
                    "slots": {},
                    "reasoning": "Detected email-related keywords"
                })
            elif any(kw in prompt_lower for kw in ['meeting', 'calendar', 'schedule', 'agenda']):
                return json.dumps({
                    "intent": "meetings.list",
                    "confidence": 0.9,
                    "slots": {},
                    "reasoning": "Detected meeting-related keywords"
                })
            elif any(kw in prompt_lower for kw in ['brief', 'summary', "what's up", 'catch up']):
                return json.dumps({
                    "intent": "briefing",
                    "confidence": 0.95,
                    "slots": {},
                    "reasoning": "User wants a briefing"
                })
            elif any(kw in prompt_lower for kw in ['followup', 'follow-up', 'follow up', 'pending']):
                return json.dumps({
                    "intent": "followups.list",
                    "confidence": 0.9,
                    "slots": {},
                    "reasoning": "Detected follow-up keywords"
                })
            elif any(kw in prompt_lower for kw in ['wellness', 'stress', 'tired', 'burnout', 'break']):
                return json.dumps({
                    "intent": "wellness.score",
                    "confidence": 0.85,
                    "slots": {},
                    "reasoning": "Detected wellness-related keywords"
                })
            elif any(kw in prompt_lower for kw in ['hello', 'hi ', 'hey', 'good morning', 'good afternoon']):
                return json.dumps({
                    "intent": "greeting",
                    "confidence": 1.0,
                    "slots": {},
                    "reasoning": "User greeted"
                })
            else:
                return json.dumps({
                    "intent": "general",
                    "confidence": 0.7,
                    "slots": {},
                    "reasoning": "General query"
                })

        # Smart chat agent responses
        if self.agent == "smart_chat":
            return "I'll help you with that request."

            # Generic fallback
        return "Acknowledged."

    def _generate_dynamic_mom(self, prompt: str) -> str:
        """
        Parse transcript from prompt and generate detailed, dynamic MoM.
        Extracts actual content from the meeting transcript.
        """
        import re
        import json
        
        # Extract transcript from prompt
        transcript_match = re.search(r'Transcript:\s*(.+)', prompt, re.DOTALL)
        transcript = transcript_match.group(1).strip() if transcript_match else ""
        
        if not transcript:
            return json.dumps({
                "summary": "No transcript available for this meeting.",
                "decisions": [],
                "action_items": [],
                "risks": [],
                "dependencies": []
            })
        
        lines = transcript.split('\n')
        
        # Extract participants from "Speaker X (Name, Company):" patterns
        participants = set()
        for line in lines:
            match = re.match(r'Speaker \d+ \(([^)]+)\):', line)
            if match:
                participants.add(match.group(1).split(',')[0].strip())
        
        # Identify key topics by looking for important keywords
        topics = []
        decisions = []
        action_items = []
        risks = []
        dependencies = []
        
        transcript_lower = transcript.lower()
        
        # Extract specific content patterns
        for line in lines:
            line_lower = line.lower()
            # Clean up speaker prefix for all extractions
            clean = re.sub(r'^Speaker \d+ \([^)]+\):\s*', '', line).strip()
            clean = re.sub(r'^Speaker \d+:\s*', '', clean).strip()
            
            # Look for decisions (keywords: decided, agreed, approved, confirmed, let's do)
            if any(kw in line_lower for kw in ['decided', 'agreed', 'approved', 'confirmed', "let's do", 'we\'ll go with', 'that\'s the plan']):
                if clean and len(clean) > 20:
                    decisions.append(clean[:200])
            
            # Look for action items (keywords: I'll, we'll, will send, by Friday, by end of, need to)
            if any(kw in line_lower for kw in ["i'll", "we'll", "will send", "by friday", "by end of", "i will", "we will", "let me", "i can have"]):
                if clean and len(clean) > 15:
                    action_items.append(clean[:200])
            
            # Look for risks (keywords: risk, concern, worried, might, could fail, blocker, delay)
            if any(kw in line_lower for kw in ['risk', 'concern', 'worried', 'might be', 'could fail', 'blocker', 'delay', 'tight', 'challenge']):
                if clean and len(clean) > 15:
                    risks.append(clean[:200])
            
            # Look for dependencies (keywords: need access, waiting for, depends on, requires)
            if any(kw in line_lower for kw in ['need access', 'waiting for', 'depends on', 'requires', 'need from', 'connect you']):
                if clean and len(clean) > 15:
                    dependencies.append(clean[:200])
        
        # Extract key metrics/numbers mentioned
        metrics = re.findall(r'\$[\d,]+k?|\d+(?:\.\d+)?%|\d+-\d+ (?:months?|weeks?|days?)|\d+ (?:months?|weeks?|days?)', transcript)
        
        # Build summary from first few substantive lines and participants
        summary_parts = []
        if participants:
            summary_parts.append(f"Meeting between {', '.join(sorted(list(participants))[:4])}.")
        
        # Find key discussion points from early lines (skip greetings)
        skip_starts = ('thanks', 'thank you', 'welcome', 'hi ', 'hello', 'good morning', 'good afternoon')
        for line in lines[:20]:
            clean = re.sub(r'^Speaker \d+ \([^)]+\):\s*', '', line).strip()
            clean = re.sub(r'^Speaker \d+:\s*', '', clean).strip()
            if len(clean) > 40 and not clean.lower().startswith(skip_starts):
                summary_parts.append(clean[:180])
                if len(summary_parts) >= 3:
                    break
                    break
        
        if metrics:
            summary_parts.append(f"Key figures discussed: {', '.join(metrics[:5])}.")
        
        summary = ' '.join(summary_parts) if summary_parts else "Meeting discussion captured."
        
        # Deduplicate and limit
        def dedupe(items, limit=5):
            seen = set()
            result = []
            for item in items:
                key = item.lower()[:50]
                if key not in seen:
                    seen.add(key)
                    result.append(item)
                if len(result) >= limit:
                    break
            return result
        
        return json.dumps({
            "summary": summary[:500],
            "decisions": dedupe(decisions),
            "action_items": dedupe(action_items),
            "risks": dedupe(risks),
            "dependencies": dedupe(dependencies)
        })