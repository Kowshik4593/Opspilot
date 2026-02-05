# 📚 OpsPilot Codebase Index

**Last Updated:** February 5, 2026  
**Project:** OpsPilot Multi-Agent Workplace Automation System  
**Tech Stack:** Python (Backend), Next.js (Frontend), LangGraph (Orchestration)

---

## 🗂️ Directory Structure Overview

```
OpsPilot/
├── agents/                 # Specialized AI agents
├── orchestration/          # LangGraph workflows & graphs
├── backend/                # FastAPI server
├── frontend/               # Next.js web application
├── memory/                 # Vector store & episodic memory
├── governance/             # Policy enforcement & audit
├── repos/                  # Data access layer
├── config/                 # Configuration
├── data/                   # Mock data & datasets
├── tests/                  # Test suites
├── chroma_db/              # Vector database storage
└── episodes/               # Episode recordings
```

---

## 📖 Detailed Module Reference

### 🤖 AGENTS (`agents/`)
Core AI agents that handle specific domains using ReAct pattern.

| File | Purpose | Key Functions |
|------|---------|---------------|
| **email_agent.py** | Email triage & summarization | `process_email()`, `_summarize()`, `_extract_actions()`, `_draft_reply()` |
| **meeting_agent.py** | Meeting management & scheduling | `process_meeting()`, `generate_mom()`, `extract_decisions()` |
| **tasks_agent.py** | Task creation & prioritization | `process_tasks()`, `prioritize()`, `extract_actions()` |
| **followup_agent.py** | Followup tracking & reminders | `check_followups()`, `create_nudge()`, `classify_severity()` |
| **reporting_agent.py** | EOD/Weekly reports & analytics | `generate_eod_report()`, `generate_weekly_report()` |
| **wellness_agent.py** | Employee wellness scoring | `check_wellness()`, `calculate_score()`, `suggest_breaks()` |
| **react_agent.py** | General ReAct orchestrator | `step()`, `think()`, `act()`, `observe()`, `finish()` |
| **autonomous_inbox.py** | Autonomous email processing | `process_inbox()`, `auto_reply()`, `classify_urgency()` |
| **tools.py** | Tool registry & definitions | Tool implementations for agents |
| **schemas.py** | Pydantic data models | Input/output schemas for agents |
| **prompts.py** | LLM prompt templates | Shared prompts across agents |

**Key Concepts:**
- **ReAct Pattern**: Reasoning + Acting loop
- **State Management**: Track agent reasoning steps
- **Tool Calling**: Agents invoke tools from `tools.py`
- **Memory Integration**: Agents access episodic & vector memory

---

### 🔄 ORCHESTRATION (`orchestration/`)
LangGraph workflows that compose and route to agents.

| File | Purpose | Graph Type |
|------|---------|-----------|
| **super_graph.py** | Main router graph | Conditional routing to subgraphs |
| **autonomous_graph.py** | Email processing workflow | Email-specific state machine |
| **email_graph.py** | Email subgraph | Detailed email handling |
| **meeting_graph.py** | Meeting workflow | Meeting coordination |
| **meeting_subgraph.py** | Meeting details | Meeting-specific nodes |
| **task_subgraph.py** | Task processing | Task-specific workflow |
| **followup_reporting_subgraphs.py** | Followup & reporting | Reporting workflows |
| **wellness_subgraph.py** | Wellness checks | Wellness scoring flow |
| **chat_workflow.py** | Chat routing | Chat message handling |
| **common_state.py** | Shared state schema | State definitions for all graphs |
| **proactive_scheduler.py** | Proactive triggers | Scheduled agent invocations |

**Architecture:**
```
super_graph (main)
├── email_graph → autonomous_graph
├── meeting_graph
├── task_subgraph
├── followup_reporting_subgraphs
└── wellness_subgraph
```

---

### 💾 BACKEND (`backend/`)
FastAPI server exposing AI agents and data APIs.

| File | Purpose |
|------|---------|
| **app.py** | FastAPI application entry point |
| **routes_agent.py** | `/api/v1/agent/*` endpoints |
| **routes_ai.py** | `/api/v1/ai/*` AI operations |
| **routes_emails.py** | `/api/v1/emails/*` Email CRUD |
| **routes_events.py** | `/api/v1/events/*` Event management |
| **routes_followups.py** | `/api/v1/followups/*` Followup tracking |
| **routes_meetings.py** | `/api/v1/meetings/*` Meeting management |
| **routes_tasks.py** | `/api/v1/tasks/*` Task operations |
| **routes_memory.py** | `/api/v1/memory/*` Memory access |
| **routes_vector.py** | `/api/v1/vector/*` Vector store ops |
| **routes_wellness.py** | `/api/v1/wellness/*` Wellness scores |
| **routes_reports.py** | `/api/v1/reports/*` Report generation |
| **models.py** | SQLAlchemy/Pydantic models |
| **auth.py** | Authentication & authorization |
| **embeddings.py** | Embedding generation & management |
| **vectors_store.json** | Persisted vector embeddings |
| **env_validation.py** | Environment setup validation |
| **repo_adapter.py** | DataRepo integration layer |
| **worker.py** | Background task worker |
| **debug_calls.py** | Debugging utilities |
| **test_api.py** | API testing suite |
| **test_api_all.py** | Comprehensive API tests |
| **Dockerfile** | Container configuration |

**API Pattern:**
```
GET    /api/v1/emails           → List emails
POST   /api/v1/emails/analyze   → Analyze email
GET    /api/v1/agent/status     → Agent status
POST   /api/v1/agent/invoke     → Invoke agent
```

---

### 🎨 FRONTEND (`frontend/`)
Next.js web application for user interface.

#### Pages
| Page | Path | Features |
|------|------|----------|
| **Dashboard** | `src/app/page.tsx` | Overview, quick stats |
| **Mail** | `src/app/mail/page.tsx` | Email client, inbox, compose |
| **Tasks** | `src/app/tasks/page.tsx` | Task list, creation, tracking |
| **Calendar** | `src/app/calendar/page.tsx` | Meeting scheduler, availability |
| **Assistant** | `src/app/assistant/page.tsx` | AI chat, reasoning display |
| **Notifications** | `src/app/notifications/page.tsx` | Alert center, approvals |
| **Reports** | `src/app/reports/page.tsx` | EOD/Weekly reports |
| **Wellness** | `src/app/wellness/page.tsx` | Wellness score, breaks, mood |
| **Activity** | `src/app/activity/page.tsx` | Agent monitoring, traces |

#### Components
| Location | Contains |
|----------|----------|
| `src/components/layout/` | Navigation, header, main layout |
| `src/components/ui/` | Button, Card, Badge, theme components |

#### Utilities
| File | Purpose |
|------|---------|
| `src/lib/api.ts` | API client & mock data loader |
| `src/lib/types.ts` | TypeScript interfaces |

**Key Features:**
- Next.js App Router
- Tailwind CSS styling
- Real-time updates
- Mock data loading
- API integration

---

### 🧠 MEMORY (`memory/`)
Vector and episodic memory systems for agent learning.

| File | Purpose |
|------|---------|
| **vector_store.py** | ChromaDB wrapper, embedding search |
| **episodic_memory.py** | Episode recording & retrieval |

**Features:**
- Vector similarity search
- Episode persistence
- Context-aware memory retrieval
- Learning from past interactions

---

### 🛡️ GOVERNANCE (`governance/`)
Policy enforcement, audit logging, and cost management.

| File | Purpose |
|------|---------|
| **gateway.py** | Policy gate for actions |
| **litellm_gateway.py** | Enhanced LLM gateway with routing |
| **audit.py** | Audit trail logging |
| **usage.py** | LLM usage tracking & budgets |
| **policies.json** | Policy definitions (approval rules, limits) |
| **approval.py** | Approval workflow management |

**Governance Aspects:**
- ✅ Approval gates for sensitive actions
- 📊 Token & cost tracking
- 🔍 Audit logging
- 📋 Policy enforcement
- 🚦 Rate limiting

---

### 📊 DATA (`data/`, `repos/`)
Data access layer and mock datasets.

**DataRepo (`repos/data_repo.py`):**
- Centralized data access interface
- Mock JSON data loading
- User, email, task, meeting data access
- Abstraction over physical storage

**Mock Data Structure:**
```
data/mock_data_json/
├── users.json              # User profiles
├── emails/
│   ├── inbox.json         # Email messages
│   └── email_threads.json # Email threads
├── tasks/
│   └── tasks.json         # Task list
├── calendar/
│   ├── meetings.json      # Meeting schedule
│   ├── mom.json           # Minutes of meeting
│   └── transcripts/       # Meeting transcripts
├── nudges/
│   └── followups.json     # Followup items
└── reporting/
    ├── eod_reports.json
    └── weekly_reports.json
```

---

### ⚙️ CONFIG (`config/`)
Centralized configuration management.

| File | Purpose |
|------|---------|
| **settings.py** | Environment-based settings, paths |

**Key Settings:**
```python
SETTINGS = {
    "env": "dev|prod",
    "data": { ... },           # Data paths
    "governance": { ... },     # Policy config
    "agents": { ... },         # Agent settings
}
```

---

### 🧪 TESTS (`tests/`)
Test suites and quality assurance.

| File | Purpose |
|------|---------|
| **comprehensive_quality_tests.py** | Full integration tests |
| **quality_test_report.json** | Test results |

---

### 🗄️ CHROMA_DB (`chroma_db/`)
Vector database persistence and memory storage.

| File | Purpose |
|------|---------|
| **chroma.sqlite3** | Vector DB file |
| **chat_manager_memory.json** | Chat memory |
| **email_agent_memory.json** | Email agent memory |
| **reporting_agent_memory.json** | Reporting memory |
| **super_graph_memory.json** | Main graph memory |

---

### 📹 EPISODES (`episodes/`)
Recorded agent episodes for learning and debugging.

| File | Purpose |
|------|---------|
| **email_agent_episodes.json** | Recorded email processing |

---

## 🔗 Data Flow

### Email Processing Flow
```
User Email
    ↓
[super_graph] → classify_intent
    ↓
[autonomous_graph] → email_agent (summarize, extract, draft)
    ↓
[governance] → approval gate
    ↓
[memory] → episodic storage
    ↓
API Response + UI Update
```

### Key Interactions

**Agent → Tool Invocation:**
```
agents/react_agent.py
    ↓
agents/tools.py (tool registry)
    ↓
repos/data_repo.py (data access)
```

**Agent → Memory:**
```
agents/[agent_name].py
    ↓
memory/vector_store.py
memory/episodic_memory.py
```

**Agent → Governance:**
```
agents/react_agent.py
    ↓
governance/gateway.py (policy check)
    ↓
governance/audit.py (logging)
governance/usage.py (cost tracking)
```

---

## 🚀 Key Workflows

### 1. Email Processing
- `autonomous_inbox.py` monitors inbox
- `email_agent.py` summarizes & extracts actions
- `tools.py` provides email tools
- `governance/gateway.py` approves sensitive actions
- Results stored in `memory/vector_store.py`

### 2. Meeting Management
- `meeting_agent.py` processes meetings
- `meeting_subgraph.py` orchestrates workflow
- Generates minutes of meeting (MoM)
- Tracks decisions & followups

### 3. Task Management
- `tasks_agent.py` prioritizes tasks
- `task_subgraph.py` routes task operations
- Integration with followup system

### 4. Wellness Tracking
- `wellness_agent.py` calculates wellness score
- `wellness_subgraph.py` orchestrates checks
- Proactive recommendations via `proactive_scheduler.py`

### 5. Reporting
- `reporting_agent.py` generates EOD/Weekly reports
- `followup_reporting_subgraphs.py` manages flow
- Aggregates across all domains

---

## 📝 Configuration Files

| File | Purpose |
|------|---------|
| **requirements.txt** | Python dependencies |
| **ARCHITECTURE.md** | System design & diagrams |
| **super_graph.md** | Super-graph mermaid diagram |
| **super_graph.png** | Visual graph layout |
| **print_graph.py** | Utility to print graph structure |
| **show_tasks.py** | Utility to display tasks |
| **.env** | Environment variables (local) |
| **.env.example** | Environment template |

---

## 🔍 Quick Reference: Finding Things

### I want to...

| Goal | Look in |
|------|----------|
| Add a new agent | `agents/` + update `orchestration/super_graph.py` |
| Change LLM prompts | `agents/prompts.py` |
| Add API endpoint | `backend/routes_*.py` |
| Create new page | `frontend/src/app/` |
| Change UI components | `frontend/src/components/ui/` |
| Add approval rule | `governance/policies.json` |
| Access data | `repos/data_repo.py` |
| Store vector memory | `memory/vector_store.py` |
| Debug agent flow | `agents/react_agent.py` + `orchestration/` |
| Check costs | `governance/usage.py` |
| View audit trail | `governance/audit.py` |

---

## 🏛️ Architecture Patterns

### Separation of Concerns
- **Agents**: Domain logic
- **Orchestration**: Workflow routing
- **Backend**: API layer
- **Frontend**: UI layer
- **Memory**: Learning layer
- **Governance**: Policy layer

### State Management
- LangGraph: Workflow state
- Agent memory: Episode storage
- Vector store: Semantic memory
- Backend: API state

### Error Handling
- ReAct pattern: Built-in error handling
- Governance gates: Approval for risky actions
- Audit trail: All operations logged
- Backup handlers: Fallback mechanisms

---

## 📊 Key Metrics Tracked

| Metric | Location |
|--------|----------|
| LLM tokens | `governance/usage.py` |
| Cost per operation | `governance/usage.py` |
| Audit trail | `governance/audit.py` |
| Agent effectiveness | `memory/episodic_memory.py` |
| Wellness score | `agents/wellness_agent.py` |

---

## 🔐 Security & Compliance

- **Authentication**: `backend/auth.py`
- **Approvals**: `governance/gateway.py`
- **Audit Logging**: `governance/audit.py`
- **Rate Limiting**: `governance/litellm_gateway.py`
- **Policy Enforcement**: `governance/policies.json`

---

## 📚 Documentation Files

| File | Contains |
|------|----------|
| **ARCHITECTURE.md** | Full system design |
| **super_graph.md** | Graph visualization |
| **frontend/README.md** | Frontend setup |
| **frontend/DESIGN.md** | UI design system |
| **frontend/QUICK_REFERENCE.md** | Frontend quick reference |
| **backend/README.md** | Backend setup |

---

## 🛠️ Development Tools

| Tool | File |
|------|------|
| Graph printer | `print_graph.py` |
| Task display | `show_tasks.py` |
| API test suite | `backend/test_api.py` |
| Comprehensive tests | `tests/comprehensive_quality_tests.py` |

---

## 📦 Dependencies

### Backend (Python)
- FastAPI, LangGraph, LLMs (OpenAI/Claude)
- ChromaDB, SQLAlchemy
- Pydantic, Uvicorn

### Frontend (Node.js)
- Next.js, React
- TypeScript, Tailwind CSS
- date-fns, lucide-react

---

## 🎯 Entry Points

| Type | Entry Point |
|------|-------------|
| **Backend** | `backend/app.py` |
| **Frontend** | `frontend/src/app/page.tsx` |
| **Main Workflow** | `orchestration/super_graph.py` |
| **CLI/Scripts** | `print_graph.py`, `show_tasks.py` |

---

## 📍 Version & Metadata

- **Project Name**: OpsPilot
- **Type**: Multi-Agent Workplace Automation
- **Main Tech**: Python + Next.js + LangGraph
- **Data Storage**: JSON + ChromaDB
- **Last Updated**: February 5, 2026

---

*This index provides a complete map of the OpsPilot codebase. Use it for navigation, onboarding, and understanding system architecture.*
