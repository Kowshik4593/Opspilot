# agents/react_agent.py
"""
ReAct Agent Implementation
==========================
Implements the Reasoning + Acting (ReAct) pattern for autonomous agent behavior.

The agent follows a loop:
1. THINK - Analyze the situation and decide what to do
2. ACT - Execute a tool/action
3. OBSERVE - Process the result
4. Repeat until task is complete or max iterations reached

This is TRUE agentic AI - the agent autonomously decides its next action.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Generator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid

from agents.tools import TOOLS, ToolExecutor, get_tools_for_llm, get_approval_required_tools


# ============================================================
# DATA STRUCTURES
# ============================================================

class StepType(Enum):
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    FINISH = "finish"
    AWAIT_APPROVAL = "await_approval"
    AWAIT_INPUT = "await_input"
    ERROR = "error"


@dataclass
class ReasoningStep:
    """A single step in the agent's reasoning process"""
    step_type: StepType
    content: str
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    iteration: int = 0


@dataclass
class AgentState:
    """Current state of the agent during execution"""
    goal: str
    email: Optional[Dict[str, Any]] = None
    context_gathered: Dict[str, Any] = field(default_factory=dict)
    actions_taken: List[str] = field(default_factory=list)
    pending_approvals: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_trace: List[ReasoningStep] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 10
    status: str = "running"  # running, completed, awaiting_approval, awaiting_input, error
    final_summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "email": self.email,
            "context_gathered": self.context_gathered,
            "actions_taken": self.actions_taken,
            "pending_approvals": self.pending_approvals,
            "reasoning_trace": [
                {
                    "step_type": step.step_type.value,
                    "content": step.content,
                    "tool_name": step.tool_name,
                    "tool_params": step.tool_params,
                    "tool_result": step.tool_result,
                    "timestamp": step.timestamp,
                    "iteration": step.iteration
                }
                for step in self.reasoning_trace
            ],
            "iteration": self.iteration,
            "status": self.status,
            "final_summary": self.final_summary
        }


# ============================================================
# PROMPTS FOR AGENT REASONING
# ============================================================

REACT_SYSTEM_PROMPT = """You are an intelligent workplace assistant agent using the ReAct (Reasoning + Acting) framework.

Your task is to autonomously process workplace items (emails, tasks, meetings) and take appropriate actions.

## How You Work:
1. THINK: Analyze the situation, what you know, what you need to find out
2. ACT: Choose ONE tool to execute (or finish if done)
3. OBSERVE: I'll show you the result
4. REPEAT: Continue until the task is complete

## Available Tools:
{tools_description}

## Tools Requiring Approval:
These actions will be queued for human review: {approval_tools}

## Current State:
- Goal: {goal}
- Iteration: {iteration}/{max_iterations}
- Actions taken so far: {actions_taken}
- Context gathered: {context_summary}

## Rules:
1. Always THINK before acting - explain your reasoning
2. Be efficient - don't repeat searches unnecessarily
3. Create tasks for actionable items
4. Draft replies for emails that need response
5. Use find_related_context when you need more information
6. Call 'finish' when you've completed all necessary actions
7. If you're unsure, use 'request_human_input'

Respond with a JSON object:
{{
    "thought": "Your reasoning about what to do next",
    "action": "tool_name",
    "action_input": {{ tool parameters }}
}}

Or if you're done:
{{
    "thought": "Summary of what was accomplished",
    "action": "finish",
    "action_input": {{
        "summary": "Brief summary",
        "actions_completed": ["action1", "action2"],
        "pending_approvals": ["approval1"]
    }}
}}
"""

INITIAL_ANALYSIS_PROMPT = """Analyze this email and decide how to handle it:

**From:** {from_email}
**Subject:** {subject}
**Received:** {received}
**Body:**
{body}

Think step by step:
1. Who is the sender and what's their relationship?
2. What is the main ask or purpose?
3. Is this urgent? What's the deadline?
4. What context do I need to gather?
5. What actions should I take?

Start by deciding your first action.
"""


# ============================================================
# REACT AGENT CLASS
# ============================================================

class ReActAgent:
    """
    ReAct Agent that autonomously processes tasks using a think-act-observe loop.
    
    This is TRUE agentic AI:
    - Agent decides what action to take at each step
    - Agent can use multiple tools in sequence
    - Agent gathers context as needed
    - Agent continues until task is complete
    """
    
    def __init__(
        self,
        repo,
        gateway=None,
        user_email: str = "kowshik.naidu@contoso.com",
        max_iterations: int = 10,
        auto_approve_reads: bool = True
    ):
        self.repo = repo
        self.gateway = gateway
        self.user_email = user_email
        self.max_iterations = max_iterations
        self.auto_approve_reads = auto_approve_reads
        self.tool_executor = ToolExecutor(repo, gateway, user_email)
    
    def process_email(self, email: Dict[str, Any]) -> Generator[ReasoningStep, None, AgentState]:
        """
        Process an email autonomously using ReAct loop.
        
        Yields ReasoningStep objects as the agent thinks and acts.
        Returns the final AgentState when complete.
        """
        # Initialize state
        state = AgentState(
            goal=f"Process email from {email.get('from_email', 'unknown')}: {email.get('subject', 'No subject')}",
            email=email,
            max_iterations=self.max_iterations
        )
        
        # Initial thinking
        initial_thought = self._format_initial_analysis(email)
        yield ReasoningStep(
            step_type=StepType.THINK,
            content=initial_thought,
            iteration=0
        )
        
        # ReAct Loop
        while state.iteration < state.max_iterations and state.status == "running":
            state.iteration += 1
            
            # THINK: Decide what to do next
            think_step = self._think(state)
            state.reasoning_trace.append(think_step)
            yield think_step
            
            # Check if agent decided to finish
            if think_step.tool_name == "finish":
                state.status = "completed"
                state.final_summary = think_step.tool_params.get("summary", "Task completed")
                break
            
            # Check if agent needs human input
            if think_step.tool_name == "request_human_input":
                state.status = "awaiting_input"
                break
            
            # ACT: Execute the chosen tool
            act_step = self._act(state, think_step.tool_name, think_step.tool_params)
            state.reasoning_trace.append(act_step)
            yield act_step
            
            # Handle actions requiring approval
            if act_step.tool_result and act_step.tool_result.get("requires_approval"):
                state.pending_approvals.append({
                    "tool": think_step.tool_name,
                    "params": think_step.tool_params,
                    "result": act_step.tool_result,
                    "iteration": state.iteration
                })
                state.actions_taken.append(f"{think_step.tool_name} (pending approval)")
            else:
                state.actions_taken.append(think_step.tool_name)
            
            # OBSERVE: Process the result and update context
            observe_step = self._observe(state, act_step)
            state.reasoning_trace.append(observe_step)
            yield observe_step
        
        # Max iterations reached
        if state.iteration >= state.max_iterations and state.status == "running":
            state.status = "completed"
            state.final_summary = f"Reached maximum iterations ({state.max_iterations}). Actions taken: {', '.join(state.actions_taken)}"
            yield ReasoningStep(
                step_type=StepType.FINISH,
                content=state.final_summary,
                iteration=state.iteration
            )
        
        return state
    
    def _think(self, state: AgentState) -> ReasoningStep:
        """Agent thinks about what to do next"""
        
        # Build context for LLM
        prompt = self._build_think_prompt(state)
        
        # Call LLM to decide next action
        if self.gateway:
            try:
                response = self.gateway.call_llm(
                    prompt,
                    temperature=0.3,
                    max_tokens=1000,
                    correlation_id=state.email.get("correlation_id") if state.email else None
                )
                decision = self._parse_llm_response(response)
            except Exception as e:
                decision = self._fallback_decision(state, str(e))
        else:
            # Simulation mode - use heuristics
            decision = self._simulate_decision(state)
        
        return ReasoningStep(
            step_type=StepType.THINK,
            content=decision.get("thought", "Analyzing..."),
            tool_name=decision.get("action"),
            tool_params=decision.get("action_input", {}),
            iteration=state.iteration
        )
    
    def _act(self, state: AgentState, tool_name: str, params: Dict[str, Any]) -> ReasoningStep:
        """Execute the chosen tool"""
        
        if not tool_name or tool_name not in TOOLS:
            return ReasoningStep(
                step_type=StepType.ERROR,
                content=f"Unknown tool: {tool_name}",
                tool_name=tool_name,
                iteration=state.iteration
            )
        
        # Execute the tool
        result = self.tool_executor.execute(tool_name, params)
        
        return ReasoningStep(
            step_type=StepType.ACT,
            content=f"Executed: {tool_name}",
            tool_name=tool_name,
            tool_params=params,
            tool_result=result,
            iteration=state.iteration
        )
    
    def _observe(self, state: AgentState, act_step: ReasoningStep) -> ReasoningStep:
        """Process the result of an action"""
        
        result = act_step.tool_result or {}
        
        # Update context based on result
        if act_step.tool_name in ["search_emails", "search_tasks", "search_meetings", "find_related_context"]:
            key = f"{act_step.tool_name}_results"
            if key not in state.context_gathered:
                state.context_gathered[key] = []
            state.context_gathered[key].append(result)
        
        elif act_step.tool_name == "get_meeting_transcript":
            state.context_gathered["transcript"] = result
        
        elif act_step.tool_name == "get_meeting_mom":
            state.context_gathered["mom"] = result
        
        elif act_step.tool_name == "analyze_email":
            state.context_gathered["email_analysis"] = result
        
        # Format observation
        if result.get("success", True):
            if result.get("requires_approval"):
                content = f"Action queued for approval: {act_step.tool_name}"
            else:
                content = self._format_observation(act_step.tool_name, result)
        else:
            content = f"Error: {result.get('error', 'Unknown error')}"
        
        return ReasoningStep(
            step_type=StepType.OBSERVE,
            content=content,
            tool_name=act_step.tool_name,
            tool_result=result,
            iteration=state.iteration
        )
    
    def _build_think_prompt(self, state: AgentState) -> str:
        """Build the prompt for the thinking step"""
        
        # Tool descriptions
        tools_desc = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in TOOLS.items()
        ])
        
        # Context summary
        context_items = []
        for key, value in state.context_gathered.items():
            if isinstance(value, list):
                context_items.append(f"- {key}: {len(value)} items")
            elif isinstance(value, dict):
                context_items.append(f"- {key}: {list(value.keys())}")
            else:
                context_items.append(f"- {key}: available")
        
        context_summary = "\n".join(context_items) if context_items else "None yet"
        
        # Recent reasoning
        recent_steps = state.reasoning_trace[-5:] if state.reasoning_trace else []
        recent_reasoning = "\n".join([
            f"[{s.step_type.value}] {s.content[:200]}..."
            if len(s.content) > 200 else f"[{s.step_type.value}] {s.content}"
            for s in recent_steps
        ])
        
        prompt = REACT_SYSTEM_PROMPT.format(
            tools_description=tools_desc,
            approval_tools=", ".join(get_approval_required_tools()),
            goal=state.goal,
            iteration=state.iteration,
            max_iterations=state.max_iterations,
            actions_taken=", ".join(state.actions_taken) if state.actions_taken else "None",
            context_summary=context_summary
        )
        
        if state.email and state.iteration == 1:
            prompt += "\n\n" + INITIAL_ANALYSIS_PROMPT.format(
                from_email=state.email.get("from_email", "Unknown"),
                subject=state.email.get("subject", "No subject"),
                received=state.email.get("received_utc", "Unknown"),
                body=state.email.get("body_text", "")[:2000]
            )
        elif recent_reasoning:
            prompt += f"\n\n## Recent Steps:\n{recent_reasoning}"
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into action decision"""
        import re
        try:
            # Try to extract JSON from response
            response_text = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            # Remove JavaScript-style comments (// ...)
            response_text = re.sub(r'//.*?(?=\n|$)', '', response_text)
            # Remove trailing commas before } or ]
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: try to extract action and thought from text
            thought = response[:500]
            
            # Try to find action from common patterns
            action_match = re.search(r'"action"\s*:\s*"([^"]+)"', response)
            action = action_match.group(1) if action_match else "think"
            
            # Try to extract action_input
            action_input = {}
            if "search" in action.lower():
                query_match = re.search(r'"query"\s*:\s*"([^"]+)"', response)
                if query_match:
                    action_input = {"query": query_match.group(1)}
            
            return {
                "thought": thought,
                "action": action,
                "action_input": action_input if action_input else {"thought": "Continuing analysis..."}
            }
    
    def _simulate_decision(self, state: AgentState) -> Dict[str, Any]:
        """
        Simulate agent decisions without LLM (for demo/testing).
        Uses heuristics based on current state.
        """
        
        email = state.email or {}
        iteration = state.iteration
        actions_taken = set(state.actions_taken)
        
        # Decision tree based on iteration and state
        
        # Iteration 1: Analyze the email content first
        if iteration == 1:
            return {
                "thought": f"New email from {email.get('from_email', 'unknown')}. Let me first understand what this is about by analyzing the content.",
                "action": "think",
                "action_input": {"thought": self._analyze_email_content(email)}
            }
        
        # Iteration 2: Search for related context
        if iteration == 2 and "find_related_context" not in actions_taken:
            # Extract key topic from email
            subject = email.get("subject", "")
            body = email.get("body_text", "")
            
            # Simple keyword extraction
            keywords = []
            for word in ["acme", "techvision", "globaltech", "api", "migration", "deadline", "urgent"]:
                if word.lower() in subject.lower() or word.lower() in body.lower():
                    keywords.append(word)
            
            topic = keywords[0] if keywords else subject.split()[0] if subject else "project"
            
            return {
                "thought": f"I should search for related context about '{topic}' to understand the full picture.",
                "action": "find_related_context",
                "action_input": {"topic": topic, "entity_type": "all", "limit": 3}
            }
        
        # Iteration 3: Check if there's a related meeting
        if iteration == 3 and "search_meetings" not in actions_taken:
            subject = email.get("subject", "")
            return {
                "thought": "Let me check if there were any recent meetings related to this topic.",
                "action": "search_meetings",
                "action_input": {"query": subject.split(":")[0] if ":" in subject else subject[:30], "limit": 3}
            }
        
        # Iteration 4: Determine actionability and create task if needed
        if iteration == 4 and "create_task" not in actions_taken:
            actionability = email.get("actionability_gt", "informational")
            
            if actionability == "actionable" or "urgent" in email.get("subject", "").lower():
                # Determine priority
                priority = "P1"  # Default high for actionable
                if "urgent" in email.get("subject", "").lower() or "asap" in email.get("body_text", "").lower():
                    priority = "P0"
                
                return {
                    "thought": f"This email is actionable and requires follow-up. Creating a {priority} task.",
                    "action": "create_task",
                    "action_input": {
                        "title": f"Respond to: {email.get('subject', 'Email')[:50]}",
                        "description": f"Follow up on email from {email.get('from_email', 'unknown')}",
                        "priority": priority,
                        "source_type": "email",
                        "source_ref_id": email.get("email_id"),
                        "tags": ["email-followup"]
                    }
                }
            else:
                return {
                    "thought": "This email is informational, no task needed. Moving to draft reply.",
                    "action": "think",
                    "action_input": {"thought": "Email categorized as informational"}
                }
        
        # Iteration 5: Draft reply if actionable
        if iteration == 5 and "draft_email_reply" not in actions_taken:
            actionability = email.get("actionability_gt", "informational")
            
            if actionability == "actionable":
                return {
                    "thought": "Drafting a professional reply to acknowledge and address the request.",
                    "action": "draft_email_reply",
                    "action_input": {
                        "email_id": email.get("email_id"),
                        "tone": "professional",
                        "key_points": ["Acknowledge receipt", "Confirm timeline", "Outline next steps"],
                        "include_context": True
                    }
                }
        
        # Iteration 6+: Finish up
        if iteration >= 5:
            # Build summary of what was done
            completed_actions = [a for a in state.actions_taken if "pending" not in a]
            pending = [a for a in state.actions_taken if "pending" in a]
            
            category = email.get("actionability_gt", "informational")
            
            return {
                "thought": f"I've completed processing this {category} email. Summary of actions taken.",
                "action": "finish",
                "action_input": {
                    "summary": f"Processed email from {email.get('from_email', 'unknown')}. Category: {category}. Actions: {len(completed_actions)} completed, {len(pending)} pending approval.",
                    "actions_completed": completed_actions,
                    "pending_approvals": pending
                }
            }
        
        # Default: continue thinking
        return {
            "thought": "Analyzing situation...",
            "action": "think",
            "action_input": {"thought": "Continuing analysis"}
        }
    
    def _analyze_email_content(self, email: Dict[str, Any]) -> str:
        """Analyze email content for initial understanding"""
        from_email = email.get("from_email", "unknown")
        subject = email.get("subject", "No subject")
        body = email.get("body_text", "")
        actionability = email.get("actionability_gt", "unknown")
        
        # Simple analysis
        is_urgent = any(w in subject.lower() or w in body.lower() 
                       for w in ["urgent", "asap", "immediately", "critical", "blocker"])
        has_deadline = any(w in body.lower() 
                         for w in ["by eod", "by end of", "deadline", "due date", "by tomorrow"])
        is_external = not from_email.endswith("@contoso.com")
        
        analysis = f"""
Email Analysis:
- Sender: {from_email} ({'External' if is_external else 'Internal'})
- Subject: {subject}
- Urgency: {'HIGH' if is_urgent else 'Normal'}
- Has Deadline: {'Yes' if has_deadline else 'No'}
- Pre-classified as: {actionability}

Next: Search for related context to understand the full picture.
"""
        return analysis.strip()
    
    def _format_initial_analysis(self, email: Dict[str, Any]) -> str:
        """Format initial analysis of the email"""
        return f"""
📧 New Email Received
━━━━━━━━━━━━━━━━━━━━━━
From: {email.get('from_email', 'Unknown')}
Subject: {email.get('subject', 'No subject')}
Received: {email.get('received_utc', 'Unknown')[:19]}

Starting autonomous processing...
"""
    
    def _format_observation(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format observation from tool result"""
        
        if tool_name == "search_emails":
            count = result.get("result", {}).get("count", 0)
            return f"Found {count} related emails"
        
        elif tool_name == "search_tasks":
            count = result.get("result", {}).get("count", 0)
            return f"Found {count} related tasks"
        
        elif tool_name == "search_meetings":
            count = result.get("result", {}).get("count", 0)
            return f"Found {count} related meetings"
        
        elif tool_name == "find_related_context":
            related = result.get("result", {}).get("related", {})
            summary = ", ".join([f"{k}: {len(v)}" for k, v in related.items()])
            return f"Context found: {summary}"
        
        elif tool_name == "get_meeting_transcript":
            has_transcript = result.get("result", {}).get("has_transcript", False)
            return f"Transcript {'retrieved' if has_transcript else 'not available'}"
        
        elif tool_name == "get_meeting_mom":
            found = result.get("result", {}).get("found", False)
            return f"Meeting minutes {'found' if found else 'not found'}"
        
        elif tool_name == "create_task":
            task = result.get("result", {}).get("task", {})
            return f"Task created: {task.get('title', 'Unknown')[:50]} ({task.get('priority', '?')})"
        
        elif tool_name == "draft_email_reply":
            return "Email reply drafted (pending approval)"
        
        elif tool_name == "think":
            return "Thought recorded"
        
        else:
            return f"Tool {tool_name} executed successfully"
    
    def _fallback_decision(self, state: AgentState, error: str) -> Dict[str, Any]:
        """Fallback decision when LLM fails"""
        return {
            "thought": f"LLM error: {error}. Using fallback logic.",
            "action": "finish",
            "action_input": {
                "summary": f"Processing interrupted due to error: {error}",
                "actions_completed": state.actions_taken,
                "pending_approvals": []
            }
        }


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def create_agent(repo, gateway=None, user_email: str = "kowshik.naidu@contoso.com") -> ReActAgent:
    """Create a configured ReAct agent"""
    return ReActAgent(
        repo=repo,
        gateway=gateway,
        user_email=user_email,
        max_iterations=10,
        auto_approve_reads=True
    )


def process_email_sync(agent: ReActAgent, email: Dict[str, Any]) -> AgentState:
    """Process an email synchronously (collects all steps)"""
    state = None
    for step in agent.process_email(email):
        pass  # Consume all steps
    # The generator returns the final state
    return state
