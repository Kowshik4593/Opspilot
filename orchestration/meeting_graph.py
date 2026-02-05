
from __future__ import annotations
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from agents.meeting_agent import MeetingAgent
from repos.data_repo import DataRepo

class MeetingState(TypedDict):
    meeting_id: str
    result: Any

def build_meeting_graph(repo: DataRepo):
    agent = MeetingAgent(repo)
    def load(s: MeetingState): return s
    def reason(s: MeetingState):
        s["result"] = agent.generate_mom(s["meeting_id"]); return s
    def validate(s: MeetingState):
        assert s["result"].meeting_id == s["meeting_id"]; return s
    g = StateGraph(MeetingState)
    g.add_node("load", load); g.add_node("reason", reason); g.add_node("validate", validate)
    g.set_entry_point("load"); g.add_edge("load","reason"); g.add_edge("reason","validate"); g.add_edge("validate", END)
    return g.compile()
