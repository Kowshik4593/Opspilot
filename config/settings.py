
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data" / "mock_data_json"))

SETTINGS = {
    "env": os.getenv("ENV", "dev"),
    "data": {
        "users": DATA_DIR / "users.json",
        "emails": {
            "inbox": DATA_DIR / "emails" / "inbox.json",
            "threads": DATA_DIR / "emails" / "email_threads.json",
        },
        "tasks": DATA_DIR / "tasks" / "tasks.json",
        "calendar": {
            "meetings": DATA_DIR / "calendar" / "meetings.json",
            "mom": DATA_DIR / "calendar" / "mom.json",
            "transcripts_dir": DATA_DIR / "calendar" / "transcripts",
        },
        "nudges": DATA_DIR / "nudges" / "followups.json",
        "reporting": {
            "eod": DATA_DIR / "reporting" / "eod.json",
            "weekly": DATA_DIR / "reporting" / "weekly.json",
        },
        "wellness": {
            "config": DATA_DIR / "wellness" / "wellness_config.json",
            "mood_history": DATA_DIR / "wellness" / "mood_history.json",
            "break_suggestions": DATA_DIR / "wellness" / "break_suggestions.json",
        },
        "governance": {
            "audit_log": DATA_DIR / "governance" / "audit_log.json",
            "llm_usage": DATA_DIR / "governance" / "llm_usage.json",
        },
    },
    "governance": {
        "policies_file": Path(os.getenv("POLICY_FILE", BASE_DIR / "governance" / "policies.json")),
        "daily_budget_usd": float(os.getenv("DAILY_BUDGET_USD", "50")),
    },
    "models": {
        "chat_model": os.getenv("AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT", "sc-rnd-gpt-4o-mini-01"),
        "embedding_model": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "ai-rnd-text-embedding-ada-002"),
        "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "azure_api_base": os.getenv("AZURE_OPENAI_API_BASE", ""),
    },
}
